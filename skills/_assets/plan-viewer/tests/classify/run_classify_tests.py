"""Tests for classify.py against a local mock Jev server (standard library only).

Usage: python run_classify_tests.py
Never contacts the real API: every request goes to 127.0.0.1. Uses a fake key set
only inside the child processes' environment. Exits non-zero on any failure.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
TOOL = ROOT / "classify.py"
VIEWER = ROOT / "plan_viewer.py"
OK = ROOT / "tests" / "ok"
FAKE_KEY = "fake-test-key-NOT-REAL-0000"

PLAN_SCORES = {  # substring of the decision text -> (P(substantive), P(procedural))
    "attention check": (0.81, 0.22),       # DP-001 decide (existing hand-written gate T-004)
    "file naming scheme": (0.08, 0.93),    # DP-002 no gate
    "colour palette": (0.66, 0.30),        # DP-003 decide -> new gate
    "archive format": (0.70, 0.80),        # DP-004 approve -> new gate
    "exactly as pre-registered": (0.74, 0.62),  # DP-005 approve (existing hand-written gate T-003)
}
KAPPA_SCORES = {
    "Kappa item alpha": (0.9, 0.2), "Kappa item bravo": (0.9, 0.2), "Kappa item charlie": (0.2, 0.8),
    "Kappa item delta": (0.1, 0.9), "Kappa item echo": (0.1, 0.9), "Kappa item foxtrot": (0.1, 0.9),
    "Kappa item golf": (0.9, 0.9),
}
SENSITIVE = [r"C:\Users\example\data\raw.csv", "/home/example/data/x.csv", "https://example.org/a?b=1",
             "someone@example.org", "@example_handle", "123e4567-e89b-12d3-a456-426614174000",
             "deadbeef1234567890", "sess_A1b2C3d4E5f6G7h8"]


# --------------------------------------------------------------------------- mock Jev

class Mock:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset()
        mock = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, obj, headers=None):
                data = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(data)

            def _auth(self):
                return self.headers.get("Authorization") == f"Bearer {FAKE_KEY}"

            def do_GET(self):
                with mock.lock:
                    mock.gets += 1
                    models = mock.models
                if not self._auth():
                    return self._send(401, {"detail": "Invalid API key"})
                if self.path.rstrip("/") != "/v1/models":
                    return self._send(404, {"detail": "not found"})
                self._send(200, models)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                with mock.lock:
                    mock.received.append(body)
                    fail = mock.fail.pop(0) if mock.fail else None
                if fail:
                    return self._send(fail, {"detail": f"mock {fail}"}, {"Retry-After": "0"})
                if not self._auth():
                    return self._send(401, {"detail": "Invalid API key"})
                if self.path != "/v1/systemone":
                    return self._send(404, {"detail": "not found"})
                m = body.get("model")
                dec = (body.get("state") or {}).get("decision", "")
                s, p = next((v for k, v in mock.scores.items() if k in dec), (0.1, 0.9))
                if m in mock.invert:
                    s, p = 1 - s, 1 - p
                vals = {"substantive": s, "procedural": p}
                answers = {}
                for q in body.get("questions", {}):
                    a = {"type": "noul", "noul": round(vals.get(q, 0.5), 2)}
                    if m in mock.extra_key:
                        a["confidence"] = 0.5
                    answers[q] = a
                self._send(200, {"model": m, "answers": answers,
                                 "usage": {"input_tokens": len(json.dumps(body)) // 4, "output_tokens": 12}},
                           {"x-typesafe-request-id": "req_" + "0" * 32})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def reset(self, models=None, fail=None, invert=(), extra_key=(), scores=None):
        self.models = models if models is not None else {"data": [{"id": "jev-1.13.0"}, {"id": "jev-1.14.0"},
                                                                  {"id": "jev-latest"}]}
        self.fail = list(fail or [])
        self.invert, self.extra_key = set(invert), set(extra_key)
        self.scores = dict(scores or {**PLAN_SCORES, **KAPPA_SCORES})
        self.received, self.gets = [], 0

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


# --------------------------------------------------------------------------- helpers

class Ctx:
    def __init__(self, tmp: Path, mock: Mock):
        self.tmp, self.mock, self.n = tmp, mock, 0
        cfg = json.loads((ROOT / "classifier.json").read_text(encoding="utf-8"))
        cfg.update({"validated": True, "workers": 4, "timeout_s": 10,
                    "retry": {"max_retries": 3, "base_delay_s": 0.01, "max_delay_s": 0.05, "jitter": 0.1}})
        self.cfg_template = cfg
        kd = tmp / "kappa"
        kd.mkdir()
        names = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf"]
        with open(kd / "test-set.jsonl", "w", encoding="utf-8", newline="\n") as f:
            for i, nm in enumerate(names, 1):
                f.write(json.dumps({"id": f"K-{i:03d}", "decision": f"Kappa item {nm}: choose an option.",
                                    "context": "Synthetic test item."}) + "\n")
        codes = {"K-001": ("yes", "no"), "K-002": ("yes", "no"), "K-003": ("yes", "yes"),
                 "K-004": ("no", "yes"), "K-005": ("no", "yes"), "K-006": ("no", "no")}  # K-007 uncoded
        (kd / "coding.json").write_text(json.dumps({"format": "coding-reply-v1", "items": {
            k: {"substantive": s, "procedural": p, "note": ""} for k, (s, p) in codes.items()}}), encoding="utf-8")
        self.test_set, self.coding = kd / "test-set.jsonl", kd / "coding.json"

    def config(self) -> Path:
        self.n += 1
        p = self.tmp / f"classifier-{self.n}.json"
        p.write_text(json.dumps(self.cfg_template, indent=2), encoding="utf-8")
        return p

    def plan(self, name, unlock=True, edit=None) -> Path:
        d = self.tmp / name
        shutil.copytree(OK, d)
        p = d / "PLAN.md"
        t = p.read_bytes().decode("utf-8")
        if unlock:
            t = re.sub(r"(?m)^Baseline lock:.*$", "Baseline lock:", t)
        if edit:
            t = edit(t)
        p.write_bytes(t.encode("utf-8"))
        return d

    def run(self, *args, key=True, cwd=None, cfg=None):
        env = {k: v for k, v in os.environ.items() if k != "TYPESAFE_API_KEY"}
        if key:
            env["TYPESAFE_API_KEY"] = FAKE_KEY
        cfg = cfg or self.config()
        cmd = [sys.executable, str(TOOL), *map(str, args), "--config", str(cfg), "--no-prompt",
               "--endpoint", self.mock.url + "/v1/systemone", "--models-endpoint", self.mock.url + "/v1/models"]
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=env, cwd=str(cwd or self.tmp), timeout=120)
        return p.returncode, p.stdout + p.stderr, cfg


def check_viewer(d):
    p = subprocess.run([sys.executable, str(VIEWER), "--check", str(d)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    return p.returncode, p.stdout + p.stderr


def classes(d):
    return json.loads((d / "Decision-Classes.json").read_text(encoding="utf-8"))


def graph_row(d, tid):
    for ln in (d / "PLAN.md").read_text(encoding="utf-8").splitlines():
        if ln.startswith(f"| {tid} |"):
            return [c.strip() for c in ln.strip().strip("|").split("|")]
    return None


def card_text(d, tid):
    t = (d / "PLAN.md").read_text(encoding="utf-8")
    m = re.search(rf"(?ms)^### {tid} .*?(?=^### |^## )", t)
    return m.group(0) if m else ""


def no_key_leak(out, d=None):
    if FAKE_KEY in out:
        return False
    if d is not None:
        for f in Path(d).rglob("*"):
            if f.is_file() and FAKE_KEY.encode() in f.read_bytes():
                return False
    return True


# --------------------------------------------------------------------------- tests

def t_estimate(c):
    d = c.plan("estimate")
    c.mock.reset()
    code, out, _ = c.run(d, "--estimate", key=False)
    ok = (code == 0 and "Decision points: 5" in out and "! python" in out and "classify.py" in out
          and "Estimated cost: $" in out and not c.mock.received and c.mock.gets == 0)
    return ok, f"exit {code}; requests {len(c.mock.received)}; gets {c.mock.gets}", out


def t_lock(c):
    d = c.plan("locked", unlock=False)
    before = (d / "PLAN.md").read_bytes()
    c.mock.reset()
    code, out, _ = c.run(d)
    ok = code == 4 and "Baseline lock" in out and not c.mock.received and (d / "PLAN.md").read_bytes() == before
    return ok, f"exit {code}", out


def _scrub_edit(t):
    old = "Choose the file naming scheme for the model output tables."
    new = ("Choose the file naming scheme for the model output tables (see " + " ".join(SENSITIVE)
           + ", and keep T-005 as the owner).")
    assert old in t
    return t.replace(old, new)


def t_full_run(c):
    d = c.plan("full", edit=_scrub_edit)
    c.mock.reset()
    code, out, cfg = c.run(d)
    c.state["full"] = d
    probs = []
    if code != 0:
        return False, f"exit {code}", out
    cl = classes(d)
    gates = {k: v["gate_task"] for k, v in cl["items"].items()}
    if gates != {"DP-001": "T-004", "DP-002": None, "DP-003": "T-010", "DP-004": "T-011", "DP-005": "T-003"}:
        probs.append(f"gates {gates}")
    if cl["classifier"]["name"] != "jev" or cl["classifier"]["version"] != "jev-1.14.0":
        probs.append("classifier meta")
    if not re.fullmatch(r"[0-9a-f]{64}", cl.get("plan_sha256_before", "")):
        probs.append("plan_sha256_before")
    if not re.fullmatch(r"[0-9a-f]{64}", cl["classifier"].get("definition_sha256", "")):
        probs.append("definition_sha256")
    if cl["items"]["DP-001"]["raw"].get("answers", {}).get("substantive", {}).get("noul") != 0.81:
        probs.append("raw response not kept")
    r10, r11, r06, r09, r02 = (graph_row(d, t) for t in ("T-010", "T-011", "T-006", "T-009", "T-002"))
    if not r10 or r10[1] != "researcher" or r10[2] != "W4" or "T-006" not in r10[6]:
        probs.append(f"T-010 row {r10}")
    if not r11 or r11[2] != "W5" or "T-009" not in r11[6]:
        probs.append(f"T-011 row {r11}")
    if "T-010" not in r06[4] or "T-011" not in r09[4] or "T-004" not in r02[4]:
        probs.append("Requires not updated")
    c10, c11 = card_text(d, "T-010"), card_text(d, "T-011")
    if "Gate-mode: decide" not in c10 or "Generated-from: DP-003" not in c10 or "control arm first" in c10:
        probs.append("T-010 card (decide, background only)")
    if ("Gate-mode: approve" not in c11 or "> A zip archive \u2014 journals accept it" not in c11
            or "CHANGELOG.md" not in c11):
        probs.append("T-011 card (approve, quotes Recommendation)")
    if not list(d.glob("PLAN.md.bak-*")):
        probs.append("no backup")
    vc, vout = check_viewer(d)
    if vc != 0:
        probs.append(f"plan_viewer --check exit {vc}: {vout.strip()[:300]}")
    if not no_key_leak(out, d):
        probs.append("key leaked")
    if len(c.mock.received) != 5:
        probs.append(f"{len(c.mock.received)} requests, expected 5")
    c.state["full_received"] = list(c.mock.received)
    return not probs, "; ".join(probs) or "gates T-010 decide, T-011 approve; --check ok", out


def t_scrub(c):
    rec = c.state.get("full_received") or []
    sent = [b["state"]["decision"] for b in rec if "file naming scheme" in b["state"]["decision"]]
    if not sent:
        return False, "DP-002 request not seen", ""
    s = sent[0]
    leaked = [x for x in SENSITIVE if x in s]
    probs = []
    if leaked:
        probs.append(f"leaked {leaked}")
    for ph in ("<PATH>", "<URL>", "<EMAIL>", "<HANDLE>", "<UUID>", "<HEX>", "<ID>"):
        if ph not in s:
            probs.append(f"missing {ph}")
    if "T-005" not in s:
        probs.append("T-005 not kept")
    sc = classes(c.state["full"])["items"]["DP-002"].get("scrub", {})
    if sc.get("path", 0) < 2 or not sc.get("email"):
        probs.append(f"scrub counts {sc}")
    if any("example" in json.dumps(b["state"]) for b in rec):
        probs.append("'example' survived in a sent state")
    return not probs, "; ".join(probs) or s, ""


def t_idempotent(c):
    d = c.state["full"]
    before = (d / "PLAN.md").read_bytes()
    c.mock.reset()
    code, out, _ = c.run(d)
    after = (d / "PLAN.md").read_bytes()
    n_cards = len(re.findall(rb"(?m)^### T-", after))
    vc, _ = check_viewer(d)
    ok = code == 0 and after == before and n_cards == 11 and vc == 0
    return ok, f"exit {code}; PLAN identical {after == before}; cards {n_cards}; --check {vc}", out


def t_retry(c):
    d = c.plan("retry")
    c.mock.reset(fail=[503])
    code, out, _ = c.run(d)
    ok = code == 0 and len(c.mock.received) == 6
    return ok, f"exit {code}; requests {len(c.mock.received)} (5 + 1 retry)", out


def t_auth(c):
    d = c.plan("auth")
    before = (d / "PLAN.md").read_bytes()
    cls_before = (d / "Decision-Classes.json").read_bytes()
    c.mock.reset(fail=[401] * 50)
    code, out, _ = c.run(d)
    ok = (code == 5 and "API error" in out and (d / "PLAN.md").read_bytes() == before
          and (d / "Decision-Classes.json").read_bytes() == cls_before and not list(d.glob("*.bak-*"))
          and no_key_leak(out, d))
    return ok, f"exit {code}; plan unchanged {(d / 'PLAN.md').read_bytes() == before}", out


NEWER = {"data": [{"id": "jev-1.13.0", "release_date": "2026-01-01"}, {"id": "jev-1.14.0", "release_date": "2026-10-14"},
                  {"id": "jev-1.15.0", "release_date": "2026-10-27"}, {"id": "jev-latest"}]}


def _version_run(c, name, **mock_kw):
    d = c.plan(name)
    cfg = c.config()
    c.mock.reset(models=NEWER, **mock_kw)
    code, out, _ = c.run(d, "--test-set", c.test_set, "--coding", c.coding, cfg=cfg)
    return d, json.loads(cfg.read_text(encoding="utf-8")), code, out


def t_version_swap(c):
    for f in c.coding.parent.glob("kappa-*.json"):
        f.unlink()
    d, cfg, code, out = _version_run(c, "v-swap")
    probs = []
    if code != 0:
        probs.append(f"exit {code}")
    if cfg["model"] != "jev-1.15.0" or not cfg.get("pin_history"):
        probs.append(f"pin {cfg['model']}")
    if code == 0 and classes(d)["classifier"]["version"] != "jev-1.15.0":
        probs.append("run did not use the new pin")
    if "PIN UPDATED" not in out or "jev-1.14.0 -> jev-1.15.0" not in out:
        probs.append("change not printed")
    if not list(c.coding.parent.glob("kappa-jev-1.15.0-*.json")):
        probs.append("no kappa report")
    return not probs, "; ".join(probs) or "swapped to jev-1.15.0", out


def t_version_shape(c):
    d, cfg, code, out = _version_run(c, "v-shape", extra_key={"jev-1.15.0"})
    ok = (code == 0 and cfg["model"] == "jev-1.14.0" and "update via an AI agent is warranted" in out
          and classes(d)["classifier"]["version"] == "jev-1.14.0")
    return ok, f"exit {code}; pin {cfg['model']}", out


def t_version_kappa_fail(c):
    d, cfg, code, out = _version_run(c, "v-kfail", invert={"jev-1.15.0"})
    ok = (code == 0 and cfg["model"] == "jev-1.14.0" and "keeping the pin" in out
          and classes(d)["classifier"]["version"] == "jev-1.14.0")
    return ok, f"exit {code}; pin {cfg['model']}", out


def t_version_unparseable(c):
    d = c.plan("v-unparse")
    c.mock.reset(models={"something": [1, 2, {"other": True}]})
    code, out, _ = c.run(d)
    ok = code == 0 and "no check possible" in out
    return ok, f"exit {code}", out


def t_import(c):
    d = c.plan("import")
    sc = {"classifier": {"name": "subagent", "version": "test-harness/test-model-1"},
          "items": {"DP-001": {"substantive": 0.8, "procedural": 0.2, "raw": {"rationale": "sample"}},
                    "DP-002": {"substantive": 0.1, "procedural": 0.9},
                    "DP-003": {"substantive": 0.2, "procedural": 0.8},
                    "DP-004": {"substantive": 0.6, "procedural": 0.7},
                    "DP-005": {"substantive": 0.7, "procedural": 0.6}}}
    f = c.tmp / "scores.json"
    f.write_text(json.dumps(sc), encoding="utf-8")
    c.mock.reset()
    code, out, _ = c.run(d, "--import", f, key=False)
    probs = []
    if code != 0:
        return False, f"exit {code}", out
    cl = classes(d)
    if cl["classifier"]["name"] != "subagent" or cl["classifier"]["version"] != "test-harness/test-model-1":
        probs.append("classifier meta")
    if cl["items"]["DP-004"]["gate_task"] != "T-010" or cl["items"]["DP-003"]["gate_task"] is not None:
        probs.append(f"gates {[(k, v['gate_task']) for k, v in cl['items'].items()]}")
    if c.mock.received or c.mock.gets:
        probs.append("network used")
    vc, vout = check_viewer(d)
    if vc != 0:
        probs.append(f"--check {vc}: {vout[:200]}")
    return not probs, "; ".join(probs) or "subagent scores baked; no network", out


def t_kappa(c):
    for f in c.coding.parent.glob("kappa-*.json"):
        f.unlink()
    c.mock.reset()
    code, out, _ = c.run("--kappa", "--test-set", c.test_set, "--coding", c.coding)
    reps = list(c.coding.parent.glob("kappa-jev-1.14.0-*.json"))
    probs = []
    if code != 0 or not reps:
        return False, f"exit {code}; reports {len(reps)}", out
    r = json.loads(reps[0].read_text(encoding="utf-8"))
    if abs(r["kappa_substantive"] - 2 / 3) > 1e-9 or abs(r["kappa_procedural"] - 2 / 3) > 1e-9:
        probs.append(f"kappa {r['kappa_substantive']}, {r['kappa_procedural']}")
    if r["skipped_uncoded"] != ["K-007"] or r["n_substantive"] != 6:
        probs.append("uncoded item not skipped")
    if r["confusion_substantive"] != {"coder_yes": {"model_yes": 2, "model_no": 1},
                                      "coder_no": {"model_yes": 0, "model_no": 3}}:
        probs.append(f"confusion {r['confusion_substantive']}")
    if abs(r["agreement_substantive"] - 5 / 6) > 1e-9:
        probs.append("agreement")
    if len(c.mock.received) != 6:
        probs.append(f"{len(c.mock.received)} requests")
    c.mock.reset(invert={"jev-1.15.0"})
    code2, out2, _ = c.run("--kappa", "--test-set", c.test_set, "--coding", c.coding, "--model", "jev-1.15.0")
    if code2 != 3:
        probs.append(f"failing kappa exit {code2}, expected 3")
    return not probs, "; ".join(probs) or "kappa 0.667 (exit 0); inverted model exit 3", out + out2


def _restore_edit(t):
    reps = [("| T-004 | researcher | W2 | pending | T-001 | none | T-005 |",
             "| T-004 | researcher | W5 | pending | T-001, T-006 | none | none |"),
            ("| T-005 | analysis | W3-W4 | pending | T-002, T-003, T-004 |",
             "| T-005 | analysis | W3-W4 | pending | T-002, T-003 |"),
            ("| T-006 | analysis | W4 | pending | T-001 | T-005 | T-007, T-008 |",
             "| T-006 | analysis | W4 | pending | T-001 | T-005 | T-007, T-008, T-004 |")]
    for a, b in reps:
        assert a in t, a
        t = t.replace(a, b)
    return t


def t_restore(c):
    d = c.plan("restore", edit=_restore_edit)
    vc, vout = check_viewer(d)
    if vc != 0:
        return False, "fixture setup invalid: " + vout[:300], vout
    before = (d / "PLAN.md").read_bytes()
    cls_before = (d / "Decision-Classes.json").read_bytes()
    c.mock.reset()
    code, out, _ = c.run(d)
    ok = (code == 1 and "restored" in out and "E-SCHEDULE" in out and (d / "PLAN.md").read_bytes() == before
          and (d / "Decision-Classes.json").read_bytes() == cls_before)
    return ok, f"exit {code}; restored {(d / 'PLAN.md').read_bytes() == before}", out


def t_key_file(c):
    d = c.plan("keyfile")
    wd = c.tmp / "OneDrive" / "work"
    wd.mkdir(parents=True)
    (wd / "jev-key.txt").write_text(FAKE_KEY + "\n", encoding="utf-8")
    c.mock.reset()
    code, out, _ = c.run(d, key=False, cwd=wd)
    ok = code == 0 and "cloud-synced" in out and "jev-key.txt in the working directory" in out and no_key_leak(out)
    return ok, f"exit {code}", out


def t_no_key(c):
    d = c.plan("nokey")
    c.mock.reset()
    code, out, _ = c.run(d, key=False)
    ok = code == 2 and "no API key" in out and not c.mock.received
    return ok, f"exit {code}", out


TESTS = [("estimate", t_estimate), ("lock refusal", t_lock), ("full run + gates + --check", t_full_run),
         ("scrubbing (as received)", t_scrub), ("re-run idempotent", t_idempotent), ("503 then success", t_retry),
         ("401 abort", t_auth), ("version: shape same + kappa pass -> swap", t_version_swap),
         ("version: shape differs -> notify", t_version_shape), ("version: kappa fail -> notify", t_version_kappa_fail),
         ("version: models unparseable -> warn", t_version_unparseable), ("--import fallback", t_import),
         ("--kappa computation", t_kappa), ("bake error -> backup restored", t_restore),
         ("key file in cloud folder -> warn", t_key_file), ("no key -> exit 2", t_no_key)]


def main():
    mock = Mock()
    failed = 0
    try:
        with tempfile.TemporaryDirectory() as tmp:
            c = Ctx(Path(tmp), mock)
            c.state = {}
            w = max(len(n) for n, _ in TESTS)
            for name, fn in TESTS:
                try:
                    ok, why, out = fn(c)
                except Exception as e:  # a crashed test is a failed test
                    ok, why, out = False, f"{type(e).__name__}: {e}", ""
                print(f"{name:<{w}}  {'PASS' if ok else 'FAIL'}  {why}")
                if not ok:
                    failed += 1
                    if out:
                        print("    output: " + " | ".join(out.strip().splitlines()[-12:]))
    finally:
        mock.stop()
    print(f"\n{len(TESTS) - failed}/{len(TESTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
