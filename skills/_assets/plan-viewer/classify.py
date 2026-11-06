"""Classify a plan's decision points (DP-###) with TypeSafe's Jev API and bake gate tasks into PLAN.md.

Usage:
    python classify.py <planning-dir> --estimate          # no network: count, cost, print the `!` command
    python classify.py <planning-dir>                     # real run (paid API; the user runs it)
    python classify.py <planning-dir> --import <scores.json>   # subagent fallback, no network
    python classify.py --kappa --test-set <jsonl> --coding <reply.json> [--model X] [--estimate]

Common options: --config <classifier.json> --definition <definition.json>
                --endpoint URL --models-endpoint URL --no-prompt

Exit codes: 0 ok; 1 plan errors (before the run, or after baking: backup restored);
2 usage, IO, config or key error; 3 kappa below kappa_min (or undefined);
4 refused: PLAN.md has a Baseline lock; 5 API error (auth, non-retryable status,
retries exhausted, unexpected response shape or answering model).

Contract: FORMAT.md sections 5 and 7; procedure and request shape: classify-README.md.
Standard library only.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import getpass
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import plan_viewer as pv  # noqa: E402  (parser and validator are reused, never edited)

TOOL_VERSION = "classify 1.0.0"
CONFIG = HERE / "classifier.json"
DEFINITION = HERE / "definition.json"
KEY_ENV = "TYPESAFE_API_KEY"
KEY_FILE = "jev-key.txt"
REQUEST_ID_HEADER = "x-typesafe-request-id"
QIDS = ("substantive", "procedural")
JEV_RE = re.compile(r"^jev-(\d+)\.(\d+)\.(\d+)$")
CLOUD_MARKERS = ("dropbox", "google drive", "googledrive", "my drive", "onedrive")
GENERATED_BY_RE = re.compile(r"^\s*generated-by\s*:\s*classify\.py\b", re.IGNORECASE)

EXIT_OK, EXIT_INVALID, EXIT_USAGE, EXIT_KAPPA, EXIT_LOCKED, EXIT_API = 0, 1, 2, 3, 4, 5


class UsageError(Exception):
    pass


class Refused(Exception):
    pass


class ApiError(Exception):
    def __init__(self, msg, status=None, auth=False):
        super().__init__(msg)
        self.status, self.auth = status, auth


class Aborted(Exception):
    pass


_SECRETS: list[str] = []


def redact(s) -> str:
    s = str(s)
    for k in _SECRETS:
        if k:
            s = s.replace(k, "<REDACTED>")
    return s


def say(*parts, err=False):
    print(redact(" ".join(str(p) for p in parts)), file=sys.stderr if err else sys.stdout, flush=True)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------- config / definition

def load_config(path: Path, args) -> dict:
    try:
        cfg = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        raise UsageError(f"cannot read config {path}: {e}")
    for k in ("model", "threshold", "kappa_min", "endpoint", "models_endpoint"):
        if k not in cfg:
            raise UsageError(f"config {path} lacks '{k}'")
    if not JEV_RE.match(str(cfg["model"])):
        raise UsageError(f"config model must be an exact version such as jev-1.14.0, not an alias: {cfg['model']!r}")
    cfg = dict(cfg)
    cfg["_path"] = path
    if getattr(args, "endpoint", None):
        cfg["endpoint"] = args.endpoint
    if getattr(args, "models_endpoint", None):
        cfg["models_endpoint"] = args.models_endpoint
    cfg.setdefault("workers", 8)
    cfg.setdefault("timeout_s", 60)
    cfg.setdefault("retry", {})
    cfg["retry"] = {"max_retries": 4, "base_delay_s": 0.5, "max_delay_s": 15, "jitter": 0.25, **cfg["retry"]}
    cfg.setdefault("price_usd_per_million_input_tokens", 0.042)
    cfg.setdefault("estimate_tokens_per_char", 0.25)
    if getattr(args, "workers", None):
        cfg["workers"] = args.workers
    return cfg


def load_definition(path: Path) -> dict:
    try:
        d = json.loads(path.read_text(encoding="utf-8-sig"))
        for q in QIDS:
            d["questions"][q]["question"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise UsageError(f"cannot read definition {path}: {e}")
    return d


def build_questions(defn: dict) -> dict:
    """The 'questions' object sent to Jev. Each question carries its own definition, criteria and anchors."""
    shared = (defn.get("shared") or {}).get("governing_distinction") or {}
    out = {}
    for qid in QIDS:
        q = defn["questions"][qid]
        instr = {"question": q["question"]}
        if shared.get("text"):
            instr["governing distinction"] = shared["text"]
        instr["definition"] = [x["text"] for x in q.get("definition", [])]
        if q.get("working_definition"):
            instr["working definition"] = q["working_definition"]
        instr["the answer leans towards yes when the decision"] = [x["criterion"] for x in q.get("leans_yes_when", [])]
        instr["the answer leans towards no when the decision"] = [x["criterion"] for x in q.get("leans_no_when", [])]
        instr["anchor examples"] = [
            {"decision": a["decision"],
             "expected answer": "yes (probability above 0.5)" if a["expected"] == "high" else "no (probability below 0.5)"}
            for a in q.get("anchors", [])]
        out[qid] = {"type": q.get("type", "noul"), "instructions": instr}
    return out


def definition_sha(questions: dict) -> str:
    return sha256_bytes(canon(questions))


def request_body(model: str, state: dict, questions: dict) -> dict:
    return {"model": model, "state": state, "questions": questions}


# --------------------------------------------------------------------------- scrubbing

_ID_PROTECT = re.compile(r"\b(?:DP|RS|T|D|R|A|G)-\d+\b|\bW\d+\b")
_PATH_CHARS = r"[^\s,;\"'`<>|()\[\]]"
SCRUB_RULES = [
    ("url", re.compile(r"\b(?:https?|ftp|file)://[^\s<>\"'`()\[\]]+|\bwww\.[^\s<>\"'`()\[\]]+", re.I), "<URL>"),
    ("email", re.compile(r"\b[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b"), "<EMAIL>"),
    ("uuid", re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "<UUID>"),
    ("path", re.compile(r"(?<![\w])[A-Za-z]:[\\/]" + _PATH_CHARS + r"*"), "<PATH>"),
    ("path", re.compile(r"\\\\[^\s\\/]+[\\/]" + _PATH_CHARS + r"*"), "<PATH>"),
    ("path", re.compile(r"(?<![\w.~/-])(?:~|\.{1,2})[\\/][\w.@%+-]+(?:[\\/][\w.@%+-]*)*"), "<PATH>"),
    ("path", re.compile(r"(?<![\w.~/-])/[\w.@%+-]+(?:/[\w.@%+-]+)+/?"), "<PATH>"),
    ("path", re.compile(r"(?<![\w./\\-])[\w.-]+(?:[/\\][\w.-]+){2,}[/\\]?"), "<PATH>"),
    ("path", re.compile(r"(?<![\w./\\-])[\w.-]+[/\\][\w.-]+[/\\]"), "<PATH>"),
    ("path", re.compile(r"(?<![\w./\\-])[\w.-]+[/\\][\w-]+\.[A-Za-z][A-Za-z0-9]{0,4}\b"), "<PATH>"),
    ("handle", re.compile(r"(?<![\w.])@[A-Za-z0-9_](?:[A-Za-z0-9_.-]*[A-Za-z0-9_])?"), "<HANDLE>"),
    ("session_id", re.compile(r"\b(?:sk|pk|rk|req|sess|session|tok|token|key|api|ghp|gho|xox[abp])[-_](?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{6,}\b", re.I), "<ID>"),
    ("session_id", re.compile(r"(?<![\w-])(?=[A-Za-z0-9_-]*\d)(?=[A-Za-z0-9_-]*[A-Za-z])[A-Za-z0-9_-]{20,}(?![\w-])"), "<ID>"),
    ("hex", re.compile(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,}\b", re.I), "<HEX>"),
]


def scrub(text: str) -> tuple[str, dict, float]:
    """(scrubbed text, counts by category, share of the original characters removed)."""
    if not text:
        return text, {}, 0.0
    keep: list[str] = []

    def protect(m):
        keep.append(m.group(0))
        return f"\x00{len(keep) - 1}\x00"

    s = _ID_PROTECT.sub(protect, text)
    counts: dict[str, int] = {}
    removed = 0
    for cat, rx, ph in SCRUB_RULES:
        def rep(m, cat=cat, ph=ph):
            nonlocal removed
            counts[cat] = counts.get(cat, 0) + 1
            removed += len(m.group(0))
            return ph
        s = rx.sub(rep, s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], s)
    s = s.replace("\x00", "")
    return s, counts, removed / max(1, len(text))


def scrub_state(state: dict) -> tuple[dict, dict, float]:
    out, counts, worst = {}, {}, 0.0
    for k, v in state.items():
        t, c, share = scrub(v)
        out[k] = t
        for cat, n in c.items():
            counts[cat] = counts.get(cat, 0) + n
        if k == "decision":
            worst = share
    return out, counts, worst


def add_counts(total: dict, c: dict) -> None:
    for k, v in c.items():
        total[k] = total.get(k, 0) + v


# --------------------------------------------------------------------------- planning dir

def parse_plan(d: Path):
    try:
        model, problems = pv.parse_planning(d)
    except OSError as e:
        raise UsageError(f"cannot read planning files: {e}")
    problems = problems + pv.validate(model)
    return model, problems


def plan_dps(model) -> list[dict]:
    pm = model["plan"]
    title = pm.get("name") or model["spec"].get("name") or "Plan"
    out = []
    for tid in pm["card_order"]:
        card = pm["cards"][tid]
        for dp in card["dps"]:
            out.append({"id": dp["id"], "task": tid, "dp": dp, "card": card,
                        "state": {"decision": dp["text"], "context": f"{title}. Task: {card['name']}."}})
    return out


def check_lock(model) -> None:
    lock = (model["plan"].get("lock") or "").strip()
    if lock:
        raise Refused(f"PLAN.md has 'Baseline lock: {lock}'. Classify runs before the lock only; after the lock, "
                      "a new gate enters only through a spec delta (planning-spec-reconciliation-protocol.md).")


# --------------------------------------------------------------------------- key handling

def key_file_warnings(path: Path) -> list[str]:
    out = []
    low = str(path.resolve()).replace("\\", "/").lower()
    for m in CLOUD_MARKERS:
        if m in low:
            out.append(f"WARN key-file: {KEY_FILE} sits in a cloud-synced folder ('{m}' in its path); "
                       "move it to a local, unsynced folder or use the environment variable.")
            break
    try:
        p = subprocess.run(["git", "ls-files", "--error-unmatch", path.name], cwd=str(path.parent),
                           capture_output=True, text=True, timeout=10)
        if p.returncode == 0:
            out.append(f"WARN key-file: {KEY_FILE} is tracked by Git; remove it from the index "
                       "(git rm --cached) and add it to .gitignore.")
    except (OSError, subprocess.SubprocessError):
        pass
    return out


def _has_display() -> bool:
    if sys.platform.startswith("win") or sys.platform == "darwin":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def prompt_key() -> str | None:
    if _has_display():
        try:
            import tkinter as tk
            from tkinter import simpledialog
            root = tk.Tk()
            root.withdraw()
            try:
                root.attributes("-topmost", True)
            except Exception:
                pass
            k = simpledialog.askstring("TypeSafe API key",
                                       "Paste the TypeSafe API key.\nIt is used for this run only and never saved.",
                                       show="*", parent=root)
            root.destroy()
            return k
        except Exception:
            pass
    if sys.stdin is not None and sys.stdin.isatty():
        return getpass.getpass("TypeSafe API key (hidden; used for this run only, never saved): ")
    return None


def get_key(no_prompt: bool) -> str:
    k = os.environ.get(KEY_ENV, "").strip()
    src = f"environment variable {KEY_ENV}"
    if not k:
        f = Path.cwd() / KEY_FILE
        if f.is_file():
            for w in key_file_warnings(f):
                say(w, err=True)
            try:
                k = f.read_text(encoding="utf-8-sig").strip()
            except OSError as e:
                raise UsageError(f"cannot read {KEY_FILE}: {e.strerror}")
            src = f"{KEY_FILE} in the working directory"
    if not k and not no_prompt:
        k = (prompt_key() or "").strip()
        src = "prompt (this run only)"
    if not k:
        raise UsageError(f"no API key: set {KEY_ENV}, put {KEY_FILE} in the working directory, or type it at the prompt")
    _SECRETS.append(k)
    say(f"API key: from {src} (not shown, not saved)")
    return k


# --------------------------------------------------------------------------- HTTP

def _opener(url: str):
    host = urllib.parse.urlsplit(url).hostname or ""
    if host in ("127.0.0.1", "localhost", "::1"):
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener()


def _http(method, url, key, body, timeout):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json", "User-Agent": TOOL_VERSION}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with _opener(url).open(req, timeout=timeout) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        try:
            raw = e.read() or b""
        except Exception:
            raw = b""
        return e.code, e.headers, raw


def _retry_after(headers) -> float | None:
    if headers is None:
        return None
    for name, scale in (("retry-after-ms", 0.001), ("retry-after", 1.0)):
        v = headers.get(name)
        if v is None:
            continue
        try:
            return max(0.0, float(v) * scale)
        except ValueError:
            continue
    return None


def call_api(method, url, key, body, cfg, abort: threading.Event | None = None):
    """(parsed JSON, headers). Retries 408, 429, every 5xx and transport errors; 401/403 abort."""
    rc = cfg["retry"]
    attempt = 0
    while True:
        if abort is not None and abort.is_set():
            raise Aborted()
        status, headers, raw, detail = None, None, b"", ""
        try:
            status, headers, raw = _http(method, url, key, body, cfg["timeout_s"])
        except (urllib.error.URLError, OSError, ValueError) as e:
            detail = f"transport error: {getattr(e, 'reason', e)}"
        if status is not None and 200 <= status < 300:
            try:
                return json.loads(raw.decode("utf-8-sig")), headers
            except (ValueError, UnicodeDecodeError) as e:
                raise ApiError(f"{method} {url}: response is not JSON ({e})", status)
        if status is not None:
            detail = f"HTTP {status}: {raw[:300].decode('utf-8', 'replace')}"
        if status in (401, 403):
            raise ApiError(f"{method} {url}: {detail} (check the API key)", status, auth=True)
        retryable = status is None or status in (408, 429) or 500 <= status <= 599
        if not retryable or attempt >= int(rc["max_retries"]):
            tail = f" after {attempt + 1} attempt(s)" if retryable else ""
            raise ApiError(f"{method} {url}: {detail}{tail}", status)
        delay = _retry_after(headers)
        if delay is None:
            delay = float(rc["base_delay_s"]) * (2 ** attempt)
            delay *= 1 + random.uniform(0, float(rc["jitter"]))
        delay = min(delay, float(rc["max_delay_s"]))
        if abort is not None:
            if abort.wait(delay):
                raise Aborted()
        else:
            time.sleep(delay)
        attempt += 1


def parse_answer(body, qids, expect_model) -> dict:
    if not isinstance(body, dict) or not isinstance(body.get("answers"), dict):
        raise ApiError("unexpected response shape: no 'answers' object")
    out = {}
    for q in qids:
        a = body["answers"].get(q)
        v = a.get("noul") if isinstance(a, dict) else None
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not (0 <= v <= 1):
            raise ApiError(f"unexpected response shape: answers.{q}.noul is not a probability")
        out[q] = float(v)
    if body.get("model") != expect_model:
        raise ApiError(f"answering model {body.get('model')!r} differs from the pin {expect_model!r}; run stopped")
    return out


def classify_states(cfg, key, model, questions, states: dict) -> dict:
    """{item id: result}; one call per item with both questions, concurrent and bounded."""
    abort = threading.Event()

    def one(iid, state):
        body, headers = call_api("POST", cfg["endpoint"], key, request_body(model, state, questions), cfg, abort)
        scores = parse_answer(body, QIDS, model)
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        return {"substantive": scores["substantive"], "procedural": scores["procedural"],
                "model": body.get("model"), "request_id": headers.get(REQUEST_ID_HEADER) if headers else None,
                "usage": usage, "raw": body}

    results, first_err = {}, None
    with cf.ThreadPoolExecutor(max_workers=max(1, int(cfg["workers"]))) as ex:
        futs = {ex.submit(one, iid, st): iid for iid, st in states.items()}
        for f in cf.as_completed(futs):
            try:
                results[futs[f]] = f.result()
            except Aborted:
                continue
            except ApiError as e:
                if first_err is None or (e.auth and not first_err.auth):
                    first_err = e
                abort.set()
                for g in futs:
                    g.cancel()
    if first_err is not None:
        raise first_err
    return results


# --------------------------------------------------------------------------- version check

def _vtuple(name):
    m = JEV_RE.match(name)
    return tuple(int(x) for x in m.groups()) if m else None


def extract_versions(obj) -> set:
    """Every exact 'jev-X.Y.Z' string anywhere in the (UNVERIFIED) /v1/models response."""
    found, stack = set(), [obj]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            stack.extend(o.values())
        elif isinstance(o, list):
            stack.extend(o)
        elif isinstance(o, str) and JEV_RE.match(o.strip()):
            found.add(o.strip())
    return found


def shape(o):
    if isinstance(o, dict):
        return {k: shape(v) for k, v in sorted(o.items())}
    if isinstance(o, list):
        return [shape(o[0])] if o else []
    if isinstance(o, bool):
        return "bool"
    if isinstance(o, (int, float)):
        return "number"
    if isinstance(o, str):
        return "string"
    return "null" if o is None else type(o).__name__


def version_check(cfg, key, questions, defn, test_set, coding, def_sha) -> str:
    """Return the model to use for this run (the pin, or a newer version after a passing swap)."""
    pin = cfg["model"]
    try:
        obj, _ = call_api("GET", cfg["models_endpoint"], key, None, cfg)
    except ApiError as e:
        if e.auth:
            raise
        say(f"WARN version-check: {e}; no check possible, keeping {pin}", err=True)
        return pin
    versions = extract_versions(obj)
    if not versions:
        say(f"WARN version-check: /v1/models listed no exact jev-X.Y.Z version (response schema is UNVERIFIED); "
            f"no check possible, keeping {pin}", err=True)
        return pin
    if pin not in versions:
        say(f"WARN version-check: the pin {pin} is not listed by /v1/models; it may have been retired", err=True)
    newest = max(versions, key=_vtuple)
    if _vtuple(newest) <= _vtuple(pin):
        say(f"Version check: {pin} is current (listed: {', '.join(sorted(versions, key=_vtuple))})")
        return pin
    say(f"Version check: newer Jev version {newest} listed (pin {pin}); probing the response shape")
    probe = defn.get("probe") or {}
    pq = probe.get("question", "substantive")
    pstate = probe.get("state") or {"decision": "Version-check probe."}
    qsub = {pq: questions[pq]}
    shapes = {}
    try:
        for m in (pin, newest):
            body, _ = call_api("POST", cfg["endpoint"], key, request_body(m, pstate, qsub), cfg)
            parse_answer(body, (pq,), m)
            shapes[m] = shape(body)
    except ApiError as e:
        if e.auth:
            raise
        say(f"NOTICE version-check: probe on {newest} failed ({e}). An update via an AI agent is warranted; "
            f"keeping the pin {pin}.")
        return pin
    if shapes[pin] != shapes[newest]:
        say(f"NOTICE version-check: {newest} returns a different response shape from {pin}. "
            f"An update via an AI agent is warranted; keeping the pin {pin}.")
        say("  pinned shape: " + json.dumps(shapes[pin], sort_keys=True))
        say("  new shape:    " + json.dumps(shapes[newest], sort_keys=True))
        return pin
    if not (test_set and coding):
        say(f"NOTICE version-check: {newest} has the same response shape, but no test set/coding is configured "
            f"(classifier.json 'test_set'/'coding' or --test-set/--coding), so the kappa check cannot run; keeping {pin}.")
        return pin
    say(f"Version check: shape unchanged; re-running the coded test set on {newest}")
    rep, path = run_kappa(cfg, key, newest, questions, def_sha, test_set, coding)
    k, kmin = rep["kappa_substantive"], float(cfg["kappa_min"])
    if k is None or k < kmin:
        say(f"NOTICE version-check: kappa on {newest} is {fmt_k(k)} < {kmin} (report {path.name}); "
            f"keeping the pin {pin}. An update via an AI agent is warranted.")
        return pin
    update_pin(cfg, pin, newest, rep, path)
    return newest


def update_pin(cfg, old, new, rep, path) -> None:
    p = cfg["_path"]
    disk = json.loads(p.read_text(encoding="utf-8-sig"))
    disk["model"] = new
    disk.setdefault("pin_history", []).append({
        "from": old, "to": new, "on": now_iso(), "kappa_substantive": rep["kappa_substantive"],
        "n": rep["n_substantive"], "kappa_report": path.name})
    write_json(p, disk)
    cfg["model"] = new
    say(f"PIN UPDATED in {p.name}: model {old} -> {new} (kappa {fmt_k(rep['kappa_substantive'])} >= "
        f"{cfg['kappa_min']} on {rep['n_substantive']} coded items; report {path.name})")


# --------------------------------------------------------------------------- kappa

def fmt_k(k):
    return "undefined" if k is None else f"{k:.3f}"


def cohen_kappa(pairs) -> float | None:
    n = len(pairs)
    if n == 0:
        return None
    po = sum(1 for c, m in pairs if c == m) / n
    pc = sum(1 for c, _ in pairs if c) / n
    pm = sum(1 for _, m in pairs if m) / n
    pe = pc * pm + (1 - pc) * (1 - pm)
    if pe >= 1:
        return None
    return (po - pe) / (1 - pe)


def confusion(pairs) -> dict:
    t = {"coder_yes": {"model_yes": 0, "model_no": 0}, "coder_no": {"model_yes": 0, "model_no": 0}}
    for c, m in pairs:
        t["coder_yes" if c else "coder_no"]["model_yes" if m else "model_no"] += 1
    return t


def load_test(test_set: Path, coding: Path):
    try:
        items = [json.loads(ln) for ln in test_set.read_text(encoding="utf-8-sig").splitlines() if ln.strip()]
        cod = json.loads(coding.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        raise UsageError(f"cannot read test set / coding: {e}")
    codes = cod.get("items") if isinstance(cod, dict) else None
    if not isinstance(codes, dict):
        raise UsageError("coding file has no 'items' object")
    coded = []
    for it in items:
        c = codes.get(it.get("id"))
        if isinstance(c, dict) and c.get("substantive") in ("yes", "no"):
            coded.append((it, c))
    return items, coded


def kappa_states(coded) -> tuple[dict, dict]:
    states, counts = {}, {}
    for it, _ in coded:
        st = {"decision": it.get("decision", "")}
        if it.get("context"):
            st["context"] = it["context"]
        st, c, _share = scrub_state(st)
        add_counts(counts, c)
        states[it["id"]] = st
    return states, counts


def run_kappa(cfg, key, model, questions, def_sha, test_set: Path, coding: Path):
    items, coded = load_test(test_set, coding)
    if not coded:
        raise UsageError("no coded items in the coding file")
    states, counts = kappa_states(coded)
    res = classify_states(cfg, key, model, questions, states)
    thr = float(cfg["threshold"])
    per, sub_pairs, proc_pairs = {}, [], []
    for it, c in coded:
        r = res[it["id"]]
        ms, mp = r["substantive"] >= thr, r["procedural"] >= thr
        sub_pairs.append((c["substantive"] == "yes", ms))
        if c.get("procedural") in ("yes", "no"):
            proc_pairs.append((c["procedural"] == "yes", mp))
        per[it["id"]] = {"coder": {"substantive": c["substantive"], "procedural": c.get("procedural")},
                         "substantive": r["substantive"], "procedural": r["procedural"],
                         "model": r["model"], "request_id": r["request_id"], "raw": r["raw"]}
    tokens = sum(int(r["usage"].get("input_tokens") or 0) for r in res.values())
    rep = {
        "format": "plan-viewer-kappa-v1", "tool": TOOL_VERSION, "model": model, "run_at": now_iso(),
        "threshold": thr, "kappa_min": float(cfg["kappa_min"]), "definition_sha256": def_sha,
        "test_set": test_set.name, "test_set_sha256": sha256_bytes(test_set.read_bytes()),
        "coding": coding.name, "coding_sha256": sha256_bytes(coding.read_bytes()),
        "n_items": len(items), "n_substantive": len(sub_pairs), "n_procedural": len(proc_pairs),
        "skipped_uncoded": [it.get("id") for it in items if it.get("id") not in per],
        "kappa_substantive": cohen_kappa(sub_pairs), "kappa_procedural": cohen_kappa(proc_pairs),
        "agreement_substantive": (sum(a == b for a, b in sub_pairs) / len(sub_pairs)) if sub_pairs else None,
        "agreement_procedural": (sum(a == b for a, b in proc_pairs) / len(proc_pairs)) if proc_pairs else None,
        "confusion_substantive": confusion(sub_pairs), "confusion_procedural": confusion(proc_pairs),
        "scrub_totals": counts,
        "usage": {"input_tokens": tokens,
                  "cost_usd": tokens * float(cfg["price_usd_per_million_input_tokens"]) / 1e6},
        "items": per,
    }
    path = coding.parent / f"kappa-{model}-{dt.date.today().isoformat()}.json"
    write_json(path, rep)
    print_kappa(rep, path)
    return rep, path


def print_kappa(rep, path):
    def pct(x):
        return "-" if x is None else f"{100 * x:.1f}%"
    say(f"Kappa ({rep['model']}, threshold {rep['threshold']}): "
        f"substantive {fmt_k(rep['kappa_substantive'])} on {rep['n_substantive']} items "
        f"(agreement {pct(rep['agreement_substantive'])}); procedural {fmt_k(rep['kappa_procedural'])} "
        f"on {rep['n_procedural']} (agreement {pct(rep['agreement_procedural'])}); "
        f"skipped uncoded {len(rep['skipped_uncoded'])}")
    for name in ("substantive", "procedural"):
        t = rep[f"confusion_{name}"]
        say(f"  {name:<11}  coder yes: model yes {t['coder_yes']['model_yes']:>3}, model no {t['coder_yes']['model_no']:>3} | "
            f"coder no: model yes {t['coder_no']['model_yes']:>3}, model no {t['coder_no']['model_no']:>3}")
    say(f"  input tokens {rep['usage']['input_tokens']}, cost ${rep['usage']['cost_usd']:.6f}; report {path}")


# --------------------------------------------------------------------------- gate baking

def _short(text, n=70):
    text = " ".join(text.split())
    if len(text) <= n:
        return text.rstrip(".")
    cut = text[:n].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:.") + "..."


def gate_card_lines(gid, d, mode, s, p, thr, meta, today) -> list[str]:
    dp, owner, card = d["dp"], d["task"], d["card"]
    approve = mode == "approve"
    name = (f"Approve the recommendation on {d['id']}" if approve else f"Decide {d['id']}") + f": {_short(dp['text'])}"
    lines = [
        f"### {gid} — {name}",
        "",
        "Status: pending",
        "Type: decision",
        f"Priority: {card.get('priority') or 'required'}",
        f"Generated-from: {d['id']}",
        f"Gate-mode: {mode}",
        f"Generated-by: classify.py ({meta['name']} {meta['version']}, {today})",
        "",
        "#### Objective",
        (f"You approve or change the recommendation for {d['id']} before {owner} ({card['name']}) starts."
         if approve else f"You decide {d['id']} before {owner} ({card['name']}) starts."),
        "",
        "#### Background",
        f"- Decision: {dp['text']}",
        f"- Gates: {owner} — {card['name']}",
        f"- Classifier: substantive {s:.2f}, procedural {p:.2f} (threshold {thr}); {meta['name']} {meta['version']}",
    ]
    if approve:
        lines += ["", "#### Recommendation", f"> {dp['rec']}"]
    else:
        lines.append("- No recommendation: the decision scored substantive and not settled by a rule (Gate-mode: decide).")
    lines += [
        "",
        "#### Outputs",
        f"The decision on {d['id']}" + (" (recommendation approved or changed)" if approve else "") + ", recorded in CHANGELOG.md.",
        "",
        "#### Verification and review",
        f"- Decision recorded in CHANGELOG.md, citing {d['id']} and the option chosen.",
        "",
        "#### Decision points",
        "none",
    ]
    return lines


def _join_cells(cells) -> str:
    return "| " + " | ".join(cells) + " |"


def bake(d: Path, model, dps, scores: dict, thr: float, meta: dict):
    """Return (new PLAN.md bytes, {dp id: gate id or None}, gate modes, notes). Pure: writes nothing."""
    plan_path = d / pv.PLAN
    raw = plan_path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    nl = "\r\n" if "\r\n" in text else "\n"
    trailing = text.endswith("\n")
    lines = text.splitlines()
    doc = pv.Doc(pv.PLAN, text)
    pm = model["plan"]
    today = dt.date.today().isoformat()
    edits: list[tuple[int, int, list[str]]] = []
    notes: list[str] = []

    sec = doc.section("Task graph")
    tbl = doc.table(sec[1], sec[2])
    header = [h.strip().lower() for h in tbl["header"]]
    col: dict[str, int] = {}
    for i, h in enumerate(header):
        col.setdefault(h, i)
    rows: dict[str, list] = {}
    for ln, cells in tbl["rows"]:
        if len(cells) == len(header) and cells[col["task"]]:
            rows[cells[col["task"]]] = [ln - 1, list(cells)]
    table_end = tbl["rows"][-1][0] if tbl["rows"] else tbl["line"] + 1
    dirty: set[str] = set()
    wi = pv.wave_index(model)
    tasks = {t["id"]: t for t in pm["tasks"]}

    def add_id(tid, column, x):
        cells = rows[tid][1]
        if column not in col:
            return
        cur = pv._id_list(cells[col[column]])
        if x in cur:
            return
        cells[col[column]] = x if not cur else cells[col[column]].rstrip() + ", " + x
        dirty.add(tid)

    # researcher lane
    if not any(ln["slug"] == pv.RESEARCHER for ln in pm["lanes"]):
        lsec = doc.section("Lanes")
        ltbl = doc.table(lsec[1], lsec[2])
        lh = [h.strip().lower() for h in ltbl["header"]]
        vals = {"lane": pv.RESEARCHER, "display name": "You", "persona": "researcher (human)"}
        at = ltbl["rows"][-1][0] if ltbl["rows"] else ltbl["line"] + 1
        edits.append((at, at, [_join_cells([vals.get(h, "—") for h in lh])]))
        notes.append("added the reserved 'researcher' lane to '## Lanes'")

    csec = doc.section("Task cards")
    card_rng = {}
    for h, htext, lo, hi in doc.subsections(3, csec[1], csec[2]):
        m = pv.CARD_RE.match(htext)
        if m:
            end = hi
            while end > h + 1 and not lines[end - 1].strip():
                end -= 1
            card_rng.setdefault(m.group(1), (h, end, lo, hi))

    existing = {c["from_dp"]: tid for tid, c in pm["cards"].items() if c.get("from_dp")}
    nums = [int(x[2:]) for x in list(tasks) + list(pm["cards"]) if pv.ID_PATTERNS["task"].fullmatch(x)]
    width = max([len(x[2:]) for x in list(tasks) + list(pm["cards"])] or [3])
    nxt = (max(nums) if nums else 0) + 1
    new_rows, new_cards = [], []
    gates, modes = {}, {}

    for d_ in dps:
        dpid, owner = d_["id"], d_["task"]
        s, p = scores[dpid]["substantive"], scores[dpid]["procedural"]
        mode = pv.gate_mode_for(s, p, thr)
        gid = existing.get(dpid)
        if mode is None:
            gates[dpid] = None
            if gid:
                notes.append(f"WARN {dpid} scored below threshold, but gate {gid} (Generated-from: {dpid}) exists; "
                             f"it was kept, with no gate_task recorded. Remove it by hand if it is no longer wanted.")
            continue
        modes[dpid] = mode
        if gid:
            h, end, lo, hi = card_rng[gid]
            prelude_end = doc.first_heading(lo, hi)
            generated = any(GENERATED_BY_RE.match(lines[i]) for i in range(lo, prelude_end))
            if generated:
                gid_card = gate_card_lines(gid, d_, mode, s, p, thr, meta, today)
                if lines[h:end] != gid_card:
                    edits.append((h, end, gid_card))
                    notes.append(f"{gid}: regenerated gate card for {dpid} ({mode})")
            else:
                gm = next((i for i in range(lo, prelude_end) if pv.META_RE.match(lines[i])
                           and pv.META_RE.match(lines[i]).group(1).lower() == "gate-mode"), None)
                # pre-validation guarantees a Gate-mode line on every Generated-from card
                cur = pv.META_RE.match(lines[gm]).group(2).lower() if gm is not None else None
                if gm is not None and cur != mode:
                    edits.append((gm, gm + 1, [re.sub(r"(?i)(gate-mode\s*:\s*).*$", lambda m_: m_.group(1) + mode, lines[gm])]))
                    notes.append(f"WARN {gid}: hand-written gate card for {dpid} switched Gate-mode {cur} -> {mode}; "
                                 "its text was not regenerated, check it matches the new mode")
            # keep the gate in (or before) the DP task's wave
            gt, ot = tasks[gid], tasks[owner]
            if gt["wave_from"] in wi and ot["wave_from"] in wi and wi[gt["wave_from"]] > wi[ot["wave_from"]]:
                rows[gid][1][col["waves"]] = ot["wave_from"]
                dirty.add(gid)
                notes.append(f"{gid}: moved to wave {ot['wave_from']}, the start of {owner}")
            add_id(owner, "requires", gid)
            add_id(gid, "enables", owner)
            add_id(owner, "researcher gates", gid)
        else:
            gid = f"T-{nxt:0{width}d}"
            nxt += 1
            vals = {"task": gid, "lane": pv.RESEARCHER, "waves": tasks[owner]["wave_from"], "status": "pending",
                    "requires": "none", "soft": "none", "enables": owner, "resources": "none",
                    "delivers": "none", "write claim": "none", "researcher gates": "—",
                    "acceptance ids": "none"}
            new_rows.append(_join_cells([vals.get(h, "—") for h in header]))
            new_cards.append(gate_card_lines(gid, d_, mode, s, p, thr, meta, today))
            add_id(owner, "requires", gid)
            add_id(owner, "researcher gates", gid)
            notes.append(f"{gid}: new {mode} gate for {dpid} (gates {owner}, wave {tasks[owner]['wave_from']})")
        gates[dpid] = gid

    for tid in dirty:
        i, cells = rows[tid]
        edits.append((i, i + 1, [_join_cells(cells)]))
    if new_rows:
        edits.append((table_end, table_end, new_rows))
    if new_cards:
        at = csec[2]
        block = []
        if at > 0 and lines[at - 1].strip():
            block.append("")
        for c in new_cards:
            block += c + [""]
        if at >= len(lines):
            block = block[:-1]
        edits.append((at, at, block))

    for start, end, new in sorted(edits, key=lambda e: (e[0], e[1]), reverse=True):
        lines[start:end] = new
    out = nl.join(lines) + (nl if trailing else "")
    data = out.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    return data, gates, modes, notes


def _backup(path: Path, stamp: str) -> Path | None:
    if not path.is_file():
        return None
    b = path.with_name(f"{path.name}.bak-{stamp}")
    n = 1
    while b.exists():
        b = path.with_name(f"{path.name}.bak-{stamp}-{n}")
        n += 1
    b.write_bytes(path.read_bytes())
    return b


def write_and_validate(d: Path, model, dps, results: dict, thr: float, meta: dict, extra: dict) -> int:
    plan_path, cls_path = d / pv.PLAN, d / pv.CLASSES
    before = plan_path.read_bytes()
    cls_before = cls_path.read_bytes() if cls_path.is_file() else None
    new_plan, gates, modes, notes = bake(d, model, dps, results, thr, meta)
    items = {}
    for d_ in dps:
        r = results[d_["id"]]
        it = {"task": d_["task"], "substantive": r["substantive"], "procedural": r["procedural"],
              "class": "substantive" if r["substantive"] >= thr else "procedural",
              "gate_task": gates.get(d_["id"]), "gate_mode": modes.get(d_["id"])}
        for k in ("model", "request_id", "state_sent", "scrub"):
            if k in r:
                it[k] = r[k]
        it["raw"] = r.get("raw", {})
        items[d_["id"]] = it
    classes = {"format": "decision-classes-v1", "classifier": meta, "threshold": thr, "items": items,
               "plan_sha256_before": sha256_bytes(before), "plan_sha256_after": sha256_bytes(new_plan)}
    classes.update(extra)

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = _backup(plan_path, stamp)
    cbak = _backup(cls_path, stamp)
    say(f"Backup: {bak.name}" + (f", {cbak.name}" if cbak else ""))

    def restore():
        plan_path.write_bytes(before)
        if cls_before is None:
            if cls_path.exists():
                cls_path.unlink()
        else:
            cls_path.write_bytes(cls_before)

    try:
        plan_path.write_bytes(new_plan)
        write_json(cls_path, classes)
        m2, probs = parse_plan(d)
    except Exception as e:
        restore()
        say(f"error while writing: {e}; PLAN.md and {pv.CLASSES} restored from the backup", err=True)
        return EXIT_USAGE
    errs = [p for p in probs if p.is_error]
    warns = [p for p in probs if not p.is_error]
    for n_ in notes:
        say(("" if n_.startswith("WARN") else "  ") + n_, err=n_.startswith("WARN"))
    if errs:
        restore()
        for p in errs + warns:
            say(p, err=True)
        say(f"{len(errs)} error(s) after gate insertion; PLAN.md and {pv.CLASSES} restored from the backup", err=True)
        return EXIT_INVALID
    q = {"approve": 0, "decide": 0, "procedural/no gate": 0}
    for it in items.values():
        q[it["gate_mode"] or "procedural/no gate"] += 1
    gl = ", ".join(f"{it['gate_task']} ({it['gate_mode']}, {k})" for k, it in items.items() if it["gate_task"]) or "none"
    say(f"Quadrants: S+P approve {q['approve']}, S only decide {q['decide']}, no gate {q['procedural/no gate']}")
    say(f"Gates: {gl}")
    say(f"Wrote {pv.CLASSES} and PLAN.md; plan_viewer check: ok ({len(warns)} warning(s))")
    for p in warns:
        say(f"  {p}")
    return EXIT_OK


# --------------------------------------------------------------------------- modes

def estimate_lines(cfg, states: dict, questions) -> tuple[int, int]:
    chars = sum(len(json.dumps(request_body(cfg["model"], st, questions), ensure_ascii=False)) for st in states.values())
    return chars, math.ceil(chars * float(cfg["estimate_tokens_per_char"]))


def fmt_cost(cfg, tokens) -> str:
    c = tokens * float(cfg["price_usd_per_million_input_tokens"]) / 1e6
    return f"${c:.6f}"


def bang_command(args, kappa=False) -> str:
    parts = ["!", "python", f'"{Path(__file__).resolve().as_posix()}"']
    if kappa:
        parts.append("--kappa")
    elif args.planning_dir:
        parts.append(f'"{Path(args.planning_dir).resolve().as_posix()}"')
    cfg_arg = args.config if Path(args.config).resolve() != CONFIG.resolve() else None
    def_arg = args.definition if Path(args.definition).resolve() != DEFINITION.resolve() else None
    for flag, val in (("--config", cfg_arg), ("--definition", def_arg), ("--endpoint", args.endpoint),
                      ("--models-endpoint", args.models_endpoint), ("--test-set", args.test_set),
                      ("--coding", args.coding), ("--model", args.model if kappa else None)):
        if val:
            v = Path(val).resolve().as_posix() if flag in ("--config", "--definition", "--test-set", "--coding") else val
            parts += [flag, f'"{v}"']
    return " ".join(parts)


def resolve_test_paths(cfg, args):
    ts = args.test_set or cfg.get("test_set")
    co = args.coding or cfg.get("coding")
    return (Path(ts) if ts else None), (Path(co) if co else None)


def cmd_estimate(cfg, args, questions) -> int:
    d = Path(args.planning_dir)
    model, problems = parse_plan(d)
    dps = plan_dps(model)
    states, counts, heavy = {}, {}, []
    for x in dps:
        st, c, share = scrub_state(x["state"])
        add_counts(counts, c)
        states[x["id"]] = st
        if share > 0.4:
            heavy.append(x["id"])
    chars, tokens = estimate_lines(cfg, states, questions)
    say(f"Planning dir: {d.resolve()}")
    say(f"Decision points: {len(dps)} in {len({x['task'] for x in dps})} task card(s); requests: {len(dps)} "
        f"(one per DP, both questions in one call), model {cfg['model']}, {cfg['workers']} workers")
    say(f"Input: {chars} characters -> about {tokens} input tokens ({cfg['estimate_tokens_per_char']} tokens/char; "
        f"Jev bills input tokens only, output is free)")
    say(f"Estimated cost: {fmt_cost(cfg, tokens)} at ${cfg['price_usd_per_million_input_tokens']} per million input "
        f"tokens (x2 safety margin: {fmt_cost(cfg, 2 * tokens)})")
    ts, co = resolve_test_paths(cfg, args)
    probe_chars = 2 * len(json.dumps(request_body(cfg["model"], {"decision": "x" * 120},
                                                  {"substantive": questions["substantive"]}), ensure_ascii=False))
    ptok = math.ceil(probe_chars * float(cfg["estimate_tokens_per_char"]))
    extra = f"Version check: GET /v1/models first; only if a newer Jev version is listed: 2 probe calls (~{ptok} tokens)"
    if ts and co and ts.is_file() and co.is_file():
        _, coded = load_test(ts, co)
        kst, _ = kappa_states(coded)
        _, ktok = estimate_lines(cfg, kst, questions)
        extra += f" + kappa re-run on {len(coded)} coded items (~{ktok} tokens, {fmt_cost(cfg, ktok)})"
    else:
        extra += "; no test set/coding configured, so a newer version would not be swapped in"
    say(extra)
    say("Scrub counts: " + (", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "none"))
    if heavy:
        say("WARN scrub: heavily scrubbed (over 40% removed), classification doubtful: " + ", ".join(heavy), err=True)
    lock = (model["plan"].get("lock") or "").strip()
    if lock:
        say(f"NOTE: PLAN.md has 'Baseline lock: {lock}', so the real run will refuse (exit 4).")
    errs = [p for p in problems if p.is_error and p.rule != "E-CLASSES"]
    if errs:
        say(f"NOTE: the plan has {len(errs)} error(s) now; the real run will refuse until they are fixed.")
    say("Agents never run paid calls. Run this yourself in chat:")
    say(bang_command(args))
    return EXIT_OK


def cmd_kappa(cfg, args, questions, def_sha) -> int:
    ts, co = resolve_test_paths(cfg, args)
    if not (ts and co):
        raise UsageError("--kappa needs --test-set and --coding (or 'test_set'/'coding' in classifier.json)")
    model = args.model or cfg["model"]
    if not JEV_RE.match(model):
        raise UsageError(f"--model must be an exact version such as jev-1.14.0, not {model!r}")
    if args.estimate:
        _, coded = load_test(ts, co)
        st, _ = kappa_states(coded)
        chars, tok = estimate_lines(cfg, st, questions)
        say(f"Kappa run: {len(coded)} coded items -> {len(coded)} requests, ~{tok} input tokens, "
            f"{fmt_cost(cfg, tok)} (x2: {fmt_cost(cfg, 2 * tok)}), model {model}")
        say("Agents never run paid calls. Run this yourself in chat:")
        say(bang_command(args, kappa=True))
        return EXIT_OK
    key = get_key(args.no_prompt)
    rep, _ = run_kappa(cfg, key, model, questions, def_sha, ts, co)
    k = rep["kappa_substantive"]
    ok = k is not None and k >= float(cfg["kappa_min"])
    say(f"Kappa gate: {'PASS' if ok else 'FAIL'} (substantive {fmt_k(k)} vs kappa_min {cfg['kappa_min']})")
    return EXIT_OK if ok else EXIT_KAPPA


def _prepare_run(args):
    d = Path(args.planning_dir)
    if not d.is_dir():
        raise UsageError(f"not a directory: {d}")
    model, problems = parse_plan(d)
    check_lock(model)
    errs = [p for p in problems if p.is_error and p.rule != "E-CLASSES"]
    if errs:
        for p in errs:
            say(p, err=True)
        say(f"{len(errs)} error(s) in the plan; fix them before classifying (nothing sent, nothing written)", err=True)
        return d, model, None
    return d, model, plan_dps(model)


def cmd_run(cfg, args, defn, questions, def_sha) -> int:
    d, model, dps = _prepare_run(args)
    if dps is None:
        return EXIT_INVALID
    if not dps:
        say("No decision points in PLAN.md; nothing to classify.")
        return EXIT_OK
    if not cfg.get("validated"):
        # Reliability gate: Jev may write gates only after its definition has passed the kappa check.
        say("Refused: the Jev definition has not passed the reliability gate (classifier.json 'validated' is false). "
            "Run --kappa until it passes, or use the subagent fallback (--import). Nothing was sent.")
        return EXIT_USAGE
    key = get_key(args.no_prompt)
    ts, co = resolve_test_paths(cfg, args)
    pin = version_check(cfg, key, questions, defn, ts, co, def_sha)
    states, scrubs, totals = {}, {}, {}
    for x in dps:
        st, c, share = scrub_state(x["state"])
        states[x["id"]], scrubs[x["id"]] = st, c
        add_counts(totals, c)
        if share > 0.4:
            say(f"WARN scrub: {x['id']} lost {share:.0%} of its text to scrubbing; classification doubtful", err=True)
    say("Scrub counts: " + (", ".join(f"{k} {v}" for k, v in sorted(totals.items())) or "none"))
    say(f"Classifying {len(dps)} decision point(s) with {pin} ({cfg['workers']} workers)")
    res = classify_states(cfg, key, pin, questions, states)
    for x in dps:
        res[x["id"]]["state_sent"] = states[x["id"]]
        res[x["id"]]["scrub"] = scrubs[x["id"]]
    tokens = sum(int(r["usage"].get("input_tokens") or 0) for r in res.values())
    cost = tokens * float(cfg["price_usd_per_million_input_tokens"]) / 1e6
    say(f"Cost incurred: {tokens} input tokens, ${cost:.6f}")
    meta = {"name": "jev", "version": pin, "run_at": now_iso(), "definition_sha256": def_sha,
            "tool": TOOL_VERSION, "endpoint": cfg["endpoint"]}
    extra = {"scrub_totals": totals, "usage": {"input_tokens": tokens, "cost_usd": cost}}
    return write_and_validate(d, model, dps, res, float(cfg["threshold"]), meta, extra)


def cmd_import(cfg, args, def_sha) -> int:
    d, model, dps = _prepare_run(args)
    if dps is None:
        return EXIT_INVALID
    try:
        src = json.loads(Path(args.import_path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        raise UsageError(f"cannot read --import file: {e}")
    items = src.get("items") if isinstance(src, dict) else None
    if not isinstance(items, dict):
        raise UsageError("--import file needs an 'items' object keyed by DP-###")
    cl = src.get("classifier") if isinstance(src.get("classifier"), dict) else {}
    version = cl.get("version") or src.get("version")
    if not isinstance(version, str) or not version.strip():
        raise UsageError("--import file needs classifier.version (the subagent's harness and exact model ID)")
    known = {x["id"] for x in dps}
    unknown = sorted(set(items) - known)
    missing = sorted(known - set(items))
    if unknown or missing:
        raise UsageError("--import items do not match the plan's DPs"
                         + (f"; unknown: {', '.join(unknown)}" if unknown else "")
                         + (f"; missing: {', '.join(missing)}" if missing else ""))
    res = {}
    for dpid, it in items.items():
        try:
            s, p = it["substantive"], it["procedural"]
            for v in (s, p):
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 1:
                    raise ValueError
        except (KeyError, TypeError, ValueError):
            raise UsageError(f"--import items.{dpid}: substantive and procedural must be numbers in [0, 1]")
        res[dpid] = {"substantive": float(s), "procedural": float(p), "raw": it.get("raw", {})}
    meta = {"name": "subagent", "version": version.strip(), "run_at": cl.get("run_at") or now_iso(),
            "definition_sha256": cl.get("definition_sha256") or def_sha, "tool": TOOL_VERSION,
            "imported_from": Path(args.import_path).name}
    say(f"Importing {len(res)} subagent score(s) ({meta['version']}); no network")
    return write_and_validate(d, model, dps, res, float(cfg["threshold"]), meta, {})


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="classify.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("planning_dir", nargs="?")
    ap.add_argument("--estimate", action="store_true", help="no network: count DPs, estimate cost, print the ! command")
    ap.add_argument("--kappa", action="store_true", help="classify the coded test set and compute Cohen's kappa")
    ap.add_argument("--test-set", help="test-set .jsonl (overrides classifier.json test_set)")
    ap.add_argument("--coding", help="coding reply .json (overrides classifier.json coding)")
    ap.add_argument("--model", help="--kappa only: exact Jev version to test (default: the pin)")
    ap.add_argument("--import", dest="import_path", help="subagent scores .json; bake gates with no network")
    ap.add_argument("--endpoint", help="override the systemone endpoint (tests: local mock)")
    ap.add_argument("--models-endpoint", help="override the /v1/models endpoint (tests: local mock)")
    ap.add_argument("--config", default=str(CONFIG), help="classifier.json (default: beside this script)")
    ap.add_argument("--definition", default=str(DEFINITION), help="definition.json (default: beside this script)")
    ap.add_argument("--workers", type=int, help="concurrent requests (default: classifier.json workers)")
    ap.add_argument("--no-prompt", action="store_true", help="never open a key prompt; fail if no env var or key file")
    args = ap.parse_args(argv)
    try:
        cfg = load_config(Path(args.config), args)
        defn = load_definition(Path(args.definition))
        questions = build_questions(defn)
        def_sha = definition_sha(questions)
        if args.kappa:
            if args.planning_dir or args.import_path:
                raise UsageError("--kappa takes no planning dir and no --import")
            return cmd_kappa(cfg, args, questions, def_sha)
        if not args.planning_dir:
            raise UsageError("planning dir required (or --kappa)")
        if args.import_path and args.estimate:
            raise UsageError("--import makes no calls; --estimate does not apply")
        if args.estimate:
            return cmd_estimate(cfg, args, questions)
        if args.import_path:
            return cmd_import(cfg, args, def_sha)
        return cmd_run(cfg, args, defn, questions, def_sha)
    except UsageError as e:
        say(f"error: {e}", err=True)
        return EXIT_USAGE
    except Refused as e:
        say(f"refused: {e}", err=True)
        return EXIT_LOCKED
    except ApiError as e:
        say(f"API error: {e}. Nothing was written to the plan.", err=True)
        return EXIT_API


if __name__ == "__main__":
    sys.exit(main())
