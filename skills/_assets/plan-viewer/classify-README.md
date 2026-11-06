# classify.py: decision-point classifier (Jev)

Classifies every `DP-###` in a plan's `PLAN.md` with two independent yes/no questions (substantive, procedural). It writes `Decision-Classes.json` (FORMAT §7) and bakes one `researcher`-lane gate task into `PLAN.md` for each DP whose substantive score is at or above the threshold (FORMAT §5). It implements `planning-decision-points-protocol.md` §2 to §5. Standard library only.

Files beside the script:

| File | Role |
|---|---|
| `classify.py` | the tool |
| `classifier.json` | the pin and the settings: `model`, `threshold`, `kappa_min`, `endpoint`, `models_endpoint`, `test_set`/`coding` (user-local, may be null), `workers`, `timeout_s`, `retry`, price, estimate factor, `pin_history` |
| `definition.json` | the approved question texts (verbatim), the definitions, the criteria, the anchors and the version-check probe |
| `tests/classify/run_classify_tests.py` | tests against a local mock Jev server |

## Usage

```
python classify.py <planning-dir> --estimate                 # no network
python classify.py <planning-dir>                            # real run (paid)
python classify.py <planning-dir> --import <scores.json>     # subagent fallback, no network
python classify.py --kappa --test-set <jsonl> --coding <reply.json> [--model jev-X.Y.Z] [--estimate]
```

Options: `--config`, `--definition`, `--endpoint`, `--models-endpoint` (the tests point these at the mock), `--test-set`/`--coding` (they override `classifier.json`, and the version check uses them too), `--workers`, `--no-prompt`.

## Cost rule

Agents never run a call that reaches the paid API. An agent runs `--estimate`, which prints the DP count, the request count, the estimated input tokens and cost, and the extra cost of a version check. It then prints the exact `!` command for the user to run in chat. Jev bills input tokens only, at $0.042 per million (`jev-api.md` §8, not shipped in this repo). Output is free.

The estimate uses 0.25 tokens per request character, against the 0.21 measured in prior projects, and also shows a ×2 margin. With the current definition, one DP request is about 2k input tokens, roughly $0.0001. The real run prints the cost it actually incurred, from `usage.input_tokens`, and records it in `Decision-Classes.json` (`usage`).

## Key handling

The key is looked up in this order:

1. the environment variable `TYPESAFE_API_KEY`;
2. `jev-key.txt` in the **current working directory**;
3. a masked `tkinter` dialog;
4. `getpass` on a terminal when no display is available.

`--no-prompt` skips steps 3 and 4. The key is used for that run only. It is never written, logged or printed, and it is redacted from every error text.

When `jev-key.txt` is used, the script warns if Git tracks the file (`git ls-files --error-unmatch`, best effort) or if its path contains Dropbox, Google Drive, My Drive or OneDrive.

## Real run, step by step

1. Parse `PLAN.md` with `plan_viewer.parse_planning`/`validate`. The run refuses with exit 4 if `Baseline lock:` has a value. It also refuses, with exit 1, if the plan has errors. `E-CLASSES` is ignored here, because the file is about to be replaced. This check happens before any key lookup or network call.
2. Look up the key.
3. **Version check.** `GET models_endpoint`. Its schema is UNVERIFIED, so every exact `jev-X.Y.Z` string anywhere in the response is collected. Aliases are ignored. If none parse, the run prints a WARN ("no check possible") and keeps the pin.
   - If a newer version is listed, the probe in `definition.json` (the substantive question about one anchor decision, with no project data) is sent to the pin and to the new version, and the response shapes are compared. A shape is the recursive keys plus value types.
   - If the shapes differ, the run prints the NOTICE "update via an AI agent is warranted" and keeps the pin. The run continues on the pin.
   - If the shapes match, the coded test set is re-run on the new version (`--kappa` logic, report written beside the coding file). If κ ≥ `kappa_min`, `classifier.json`'s `model` is updated, a `pin_history` entry is added, the change is printed, and the run uses the new version. Otherwise the run prints a notice and keeps the pin.
   - With no test set or coding configured, no swap happens.
   - A 401 or 403 here aborts the run. Any other failure of the check only warns.
4. **Scrub** each DP's state, then send **one call per DP with both questions**: 8 concurrent workers by default.
   - Statuses 408, 429 and every 5xx are retried, as are transport errors: 4 retries, 0.5 s doubling to 15 s, 25 % jitter, honouring `retry-after-ms` and `retry-after`.
   - A 401 or 403 aborts all workers.
   - Any other 4xx, exhausted retries, a missing or invalid `answers.<q>.noul`, or an answering `model` that differs from the pin aborts the run with exit 5, and nothing is written.
5. **Write and bake.** Back up `PLAN.md` (and `Decision-Classes.json`, if present) to `<name>.bak-<YYYYMMDD-HHMMSS>`. Insert or update the gates, write `Decision-Classes.json`, and re-run `plan_viewer` parse plus validate. **If any error appears, both files are restored** and the run exits 1 with the errors listed.

### Request

```json
{"model": "jev-1.14.0",
 "state": {"decision": "<scrubbed DP text>", "context": "<scrubbed '<plan title>. Task: <card name>.'>"},
 "questions": {
   "substantive": {"type": "noul", "instructions": {
       "question": "<approved text, verbatim>",
       "governing distinction": "...", "definition": ["..."], "working definition": "...",
       "the answer leans towards yes when the decision": ["..."],
       "the answer leans towards no when the decision": ["..."],
       "anchor examples": [{"decision": "...", "expected answer": "yes (probability above 0.5)"}]}},
   "procedural": {"type": "noul", "instructions": {"...": "same layout"}}}}
```

**How the definition reaches Jev.** Each question's definition, criteria and anchors travel inside its own `instructions` object, which Jev accepts as an object (`jev-api.md` §3, not shipped in this repo). They do not travel in `state`. Questions in one call cannot see each other's answers, and keeping each definition inside its own question also keeps the substantive material out of the procedural question's context, and the reverse.

`state` holds only the two fields the blind coder saw in the test set: `decision` and `context`. Question IDs are not sent to the model, so each question restates its meaning in full. Source tags and basis quotes in `definition.json` are provenance only and are not sent.

`definition_sha256` is the SHA-256 of the canonical JSON (sorted keys, compact, UTF-8) of the `questions` object sent.

### Response used

`answers.substantive.noul` and `answers.procedural.noul` are taken as P(yes), and `model` is checked against the pin. The full body is stored as `raw`, and the `x-typesafe-request-id` header as `request_id`.

## Scrub rules

Applied to `decision` and `context` before sending. The `T-`, `DP-`, `D-`, `R-`, `A-`, `RS-`, `G-` and `W<n>` IDs are protected.

| Category | Replaced by | Matches |
|---|---|---|
| `url` | `<URL>` | `http(s)://`, `ftp://`, `file://`, `www.` |
| `email` | `<EMAIL>` | `name@domain.tld` |
| `uuid` | `<UUID>` | 8-4-4-4-12 hex |
| `path` | `<PATH>` | Windows `X:\...` / `X:/...`; UNC `\\host\...`; `~/`, `./`, `../`; absolute Unix with at least 2 segments; relative paths with at least 2 separators, a trailing separator, or a file extension |
| `handle` | `<HANDLE>` | `@name` (not part of an email) |
| `session_id` | `<ID>` | prefixed tokens with a digit (`sk-`, `req_`, `sess_`, `tok_`, `key_`, `ghp_`, ...); any letter-and-digit token of 20 or more characters |
| `hex` | `<HEX>` | hex runs of 7 or more characters containing both a digit and a letter (e.g. Git SHAs) |

Counts are printed, stored per item (`scrub`) and as `scrub_totals`. The exact state sent is stored per item as `state_sent`. If a DP loses more than 40 % of its characters, the run prints a WARN, because its classification is doubtful.

## Gate baking (FORMAT §5)

For each DP, `pv.gate_mode_for(S, P, threshold)` gives the result:

- `approve` when S ≥ t and P ≥ t;
- `decide` when S ≥ t and P < t;
- no gate when S < t.

**New gate:**
- it takes the next free `T-` number, with the same zero padding;
- it gets a task-graph row: lane `researcher`, wave = the first wave of the DP's task, Requires `none`, Enables = the DP's task;
- the gate is added to the DP task's `Requires` and to its `Researcher gates` column, if that column is present;
- a card is appended to `## Task cards` with `Generated-from`, `Gate-mode` and `Generated-by: classify.py (...)`, plus Objective, Background, Outputs and Verification ("Decision recorded in CHANGELOG.md, citing DP-### and the option chosen.");
- an `approve` card quotes the DP's Recommendation verbatim. A `decide` card carries background only: no Recommendation and no Default.

**Existing gate** (a card with `Generated-from: DP-###`) is updated in place, never duplicated:
- a card the script wrote (`Generated-by: classify.py`) is regenerated;
- on a hand-written card only the `Gate-mode` line changes, with a WARN that its text was not regenerated;
- missing edges are added;
- a gate that sits in a later wave than its DP's task is moved to that task's first wave.

**DP below the threshold that already has a gate:** the gate is kept, `gate_task` is null, and the run prints a WARN to remove the gate by hand. The script never deletes a researcher gate.

If the plan has no `researcher` lane, one is added to `## Lanes`.

Re-running with the same scores on the same day leaves `PLAN.md` byte-identical.

## `Decision-Classes.json` written

FORMAT §7, plus these extras: per item `gate_mode`, `model`, `request_id`, `state_sent` and `scrub`; top level `plan_sha256_after`, `scrub_totals` and `usage`; and in `classifier`, `tool` and `endpoint`. `classifier.name` is `jev`, or `subagent` for `--import`.

## `--import` (subagent fallback, protocol §4)

The input file looks like this:

```json
{"classifier": {"name": "subagent", "version": "<harness>/<exact model id>"},
 "items": {"DP-001": {"substantive": 0.8, "procedural": 0.2, "raw": {}}}}
```

Every DP in the plan must be present, and no unknown DP may appear. Scores must be in [0, 1]. The gates are baked exactly as in a real run, with no network. `definition_sha256` comes from the file if it is given; otherwise it is the hash of the current definition.

## `--kappa`

`--kappa` classifies the coded items of the test set, sending `decision` and `context` as the coder saw them, scrubbed. Uncoded items are skipped and listed.

It reports:
- Cohen's κ for substantive (yes = score ≥ threshold) and for procedural;
- 2×2 confusion tables;
- agreement %.

It writes `kappa-<model>-<YYYY-MM-DD>.json` beside the coding file, with scores, raw responses, hashes and cost. If κ is undefined (no variation), the gate fails.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | ok (warnings and version-check notices allowed) |
| 1 | plan errors before the run, or after baking (both files restored) |
| 2 | usage, IO, config or definition error; no API key |
| 3 | `--kappa`: κ(substantive) < `kappa_min`, or undefined |
| 4 | refused: `PLAN.md` has a `Baseline lock` value |
| 5 | API error: auth, a non-retryable status, retries exhausted, unexpected response shape or answering model; nothing written |

## Tests

`python tests/classify/run_classify_tests.py` starts a mock Jev on 127.0.0.1, copies `tests/ok/` into a temp dir and uses a fake key, set only in the child environment. It never contacts the real API. Its 16 cases:

- estimate;
- lock refusal;
- a full run, with gates and `--check`;
- scrubbing, checked on what the mock received;
- an idempotent re-run;
- 503 then success;
- a 401 abort;
- the version swap, shape-differs, κ-fail and unparseable-models paths;
- `--import`;
- `--kappa`;
- restoring the backup on a bake error;
- the cloud-folder key-file warning;
- the no-key exit.
