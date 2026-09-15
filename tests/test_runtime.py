"""Portable installation and native lifecycle tests; no provider or user settings."""
import contextlib
import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer", REPO / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
sys.path.insert(0, str(REPO / "runtime/src"))
from aios_native.bookkeeping import Bookkeeper, Refused
from aios_native.ingress import hook_request

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="aios test ")
        self.base = Path(self.tmp.name).resolve()
        self.root = self.base / "AI OS"
        self.project = self.base / "sample project"
        self.project.mkdir()
        self.state = self.base / "private"
        self.args = ["--root", str(self.root), "--project", str(self.project),
                     "--slug", "sample", "--state-dir", str(self.state)]
        self.config = self.root / "config/ownership.json"

    def tearDown(self):
        # Verify the exact owned temporary root before recursive cleanup.
        self.assertEqual(Path(self.tmp.name).resolve(), self.base)
        self.assertEqual(self.base.parent, Path(tempfile.gettempdir()).resolve())
        if os.name == "nt":
            self.tmp.name = chr(92) * 2 + "?" + chr(92) + str(self.base)
        self.tmp.cleanup()

    def install(self, extra=(), expected=0):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = installer.main(self.args + list(extra))
        self.assertEqual(code, expected, output.getvalue())
        return output.getvalue()

    def cli(self, *args, payload=None, expected=0):
        run = subprocess.run([sys.executable, "-I", "-B", str(self.root / "runtime/aios.py"), *args],
                             input=json.dumps(payload) if payload is not None else None,
                             capture_output=True, text=True, timeout=35)
        self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
        return json.loads(run.stdout)

    def request(self, op, **values):
        body = {"operation": op, "key": uuid.uuid4().hex, **values}
        path = self.base / (body["key"] + ".json")
        path.write_text(json.dumps(body), encoding="utf-8")
        return body, path

    def start(self, harness="codex-cli", native="fixture"):
        result = self.cli("--harness", harness, payload={
            "hook_event_name": "SessionStart", "session_id": native,
            "cwd": str(self.project), "model": "fixture-model"})
        return json.loads(result["hookSpecificOutput"]["additionalContext"])["aios"]["activation"]

    def submit(self, op, **values):
        _, path = self.request(op, **values)
        return self.cli("--request", str(path))

    def test_dry_run_writes_nothing(self):
        self.install(["--dry-run"])
        self.assertFalse(self.root.exists())
        self.assertFalse(self.state.exists())
        self.assertEqual(list(self.project.iterdir()), [])

    def test_install_repeat_preserves_settings_and_instructions(self):
        (self.project / ".claude").mkdir()
        settings = self.project / ".claude/settings.local.json"
        settings.write_text(json.dumps({"permissions": {"deny": ["Bash(rm:*)"]},
                                        "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo prior"}]}]}}))
        (self.project / "AGENTS.md").write_text("# Existing instructions\n")
        self.install()
        before = {p: p.read_bytes() for p in self.project.rglob("*") if p.is_file()}
        second = json.loads(self.install())
        self.assertEqual(second["changed_files"], 0)
        self.assertEqual(before, {p: p.read_bytes() for p in self.project.rglob("*") if p.is_file()})
        config = json.loads(settings.read_bytes())
        self.assertEqual(config["permissions"], {"deny": ["Bash(rm:*)"]})
        self.assertEqual(len(config["hooks"]["Stop"]), 2)
        self.assertEqual(self.cli("--doctor")["status"], "ok")

    def test_both_harnesses_close_reopen_and_ignore_late_events(self):
        self.install()
        for harness in ("claude-code", "codex-cli"):
            sid = self.start(harness, harness)
            self.cli("--harness", harness, payload={"hook_event_name": "Stop", "session_id": harness,
                                                  "cwd": str(self.project)})
            self.assertTrue((self.root / "coord/sessions" / (sid + ".md")).exists())
            self.cli("--harness", harness, payload={"hook_event_name": "SessionEnd", "session_id": harness,
                                                  "cwd": str(self.project)})
            self.assertTrue((self.root / "coord/sessions/_closed" / (sid + ".md")).exists())
            self.cli("--harness", harness, payload={"hook_event_name": "PostToolUse", "session_id": harness,
                                                  "cwd": str(self.project)})
            self.assertFalse((self.root / "coord/sessions" / (sid + ".md")).exists())
            self.assertNotEqual(sid, self.start(harness, harness))

    def test_snapshot_and_summary_publish_once(self):
        self.install()
        sid = self.start()
        artifact = self.project / "output.txt"
        artifact.write_bytes(b"fixture output\n")
        self.submit("checkpoint", activation=sid, claims=[str(artifact)],
                    artifacts=[{"path": "output.txt", "text": True, "verification": "partially-verified"}])
        body, path = self.request("close", activation=sid, claims=[], summary="Fixture done",
                                  input_summary="Fixture request", relaunch="no")
        result = self.cli("--request", str(path))
        self.assertEqual(result["publication"], "complete")
        self.cli("--request", str(path))
        rows = list(csv.DictReader(io.StringIO((self.project / "interaction-log.csv").read_text(encoding="utf-8"))))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["agent_output_summary"], "Fixture done")
        assets = list(csv.DictReader(io.StringIO((self.project / "asset-registry.csv").read_text(encoding="utf-8"))))
        self.assertEqual(len(assets), 1)
        self.assertEqual((self.project / ".cowork/snapshots" / (assets[0]["ai_output_hash"] + ".snap")).read_bytes(),
                         artifact.read_bytes())
        self.assertTrue((self.root / "coord/mailbox/operator" / (sid + "-closeout.md")).exists())

    def test_claim_collision_and_release(self):
        self.install()
        a, b = self.start(native="one"), self.start(native="two")
        target = str(self.project / "shared.txt")
        self.submit("checkpoint", activation=a, claims=[target])
        _, req = self.request("checkpoint", activation=b, claims=[target])
        refused = self.cli("--request", str(req), expected=2)
        self.assertFalse(refused["continue"])
        self.submit("close", activation=a, summary="Released", relaunch="no")
        self.assertEqual(self.cli("--request", str(req))["claims"], [target])

    def test_shutdown_closes_and_stops(self):
        self.install()
        sid = self.start()
        (self.root / "coord/control/SHUTDOWN-REQUESTED.md").write_text("Operator shutdown")
        output = self.cli("--harness", "codex-cli", payload={"hook_event_name": "PreToolUse",
                          "session_id": "fixture", "cwd": str(self.project)}, expected=2)
        self.assertFalse(output["continue"])
        self.assertTrue((self.root / "coord/sessions/_closed" / (sid + ".md")).exists())

    def test_hook_does_not_persist_raw_fields(self):
        self.install()
        sentinel = "RAW_SECRET_SENTINEL_98d08"
        self.cli("--harness", "codex-cli", payload={
            "hook_event_name": "SessionStart", "session_id": "privacy",
            "cwd": str(self.project), "model": "fixture",
            "prompt": sentinel, "tool_input": {"secret": sentinel},
            "transcript_path": str(self.base / sentinel)})
        for parent in (self.state, self.root, self.project):
            if os.name == "nt":
                parent = Path(chr(92) * 2 + "?" + chr(92) + str(parent))
            for p in parent.rglob("*"):
                if p.is_file():
                    self.assertNotIn(sentinel.encode(), p.read_bytes(), str(p))

    def test_invalid_artifact_and_human_verification_refused(self):
        self.install()
        sid = self.start()
        for artifact in ({"path": "../outside"}, {"path": "background/data"},
                         {"path": "output.txt", "verification": "human-verified"}):
            _, path = self.request("checkpoint", activation=sid, artifacts=[artifact])
            self.cli("--request", str(path), expected=2)

    def test_reconcile_after_journal_fault_does_not_repeat_project_row(self):
        self.install()
        sid = self.start()
        hit = []
        def fault(stage):
            if stage == "after-journal":
                hit.append(stage)
                raise RuntimeError("simulated crash")
        req = {"operation": "close", "key": "fault-close", "activation": sid, "summary": "Recovered", "relaunch": "no"}
        with self.assertRaises(RuntimeError):
            Bookkeeper(self.config, fault=fault).execute(req)
        self.assertEqual(hit, ["after-journal"])
        bk = Bookkeeper(self.config)
        self.assertEqual(bk.execute({"operation": "reconcile", "key": "recover"})["status"], "reconciled")
        bk.execute(req)
        with (self.project / "interaction-log.csv").open() as stream:
            self.assertEqual(len(list(csv.DictReader(stream))), 1)

    def test_bad_existing_hooks_preflight_has_no_partial_effect(self):
        (self.project / ".codex").mkdir()
        (self.project / ".codex/hooks.json").write_text("{bad-json")
        self.install(expected=2)
        self.assertFalse(self.root.exists())
        self.assertFalse(self.state.exists())
        self.assertFalse((self.project / "asset-registry.csv").exists())

    def test_state_inside_project_refused(self):
        self.install(["--state-dir", str(self.project / "private")], expected=2)
        self.assertFalse(self.root.exists())

    def test_managed_runtime_change_refused(self):
        self.install()
        path = self.root / "runtime/src/aios_native/bookkeeping.py"
        path.write_bytes(path.read_bytes() + b"\n# changed\n")
        self.cli("--doctor", expected=2)
        self.install(expected=2)

    def test_active_session_prevents_reconfiguration(self):
        self.install()
        self.start()
        self.install(expected=2)

    def test_idle_prompt_resumes_but_tool_does_not(self):
        self.install()
        sid = self.start()
        from datetime import datetime, timedelta, timezone
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        bk = Bookkeeper(self.config, clock=lambda: future)
        payload = {"hook_event_name": "UserPromptSubmit", "session_id": "fixture", "cwd": str(self.project)}
        self.assertEqual(hook_request(bk, payload, "codex-cli")["operation"], "resume")
        payload["hook_event_name"] = "PreToolUse"
        self.assertEqual(hook_request(bk, payload, "codex-cli")["operation"], "checkpoint")

    def test_generated_hook_command_executes_in_space_path(self):
        self.install()
        for harness in ("claude-code", "codex-cli"):
            rel = ".claude/settings.local.json" if harness == "claude-code" else ".codex/hooks.json"
            h = json.loads((self.project / rel).read_bytes())["hooks"]["SessionStart"][0]["hooks"][0]
            command = [h["command"], *h["args"]] if "args" in h else h["command"]
            run = subprocess.run(command, shell="args" not in h,
                                 input=json.dumps({"hook_event_name": "SessionStart", "session_id": "cmd-" + harness,
                                                   "cwd": str(self.project), "model": "fixture"}),
                                 capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("additionalContext", run.stdout)

    def test_status_and_bounded_intake(self):
        self.install()
        sid = self.start()
        self.assertEqual(self.cli("--status")["sessions"][0]["id"], sid)
        intake = self.cli("--intake", "--harness", "codex-cli", "--native-id", "fixture",
                          "--workspace", str(self.project))
        self.assertEqual(intake["errors"], [])

    def test_project_instructions_are_portable(self):
        self.install()
        for name in ("AGENTS.md", "CLAUDE.md"):
            self.assertNotIn(str(self.base), (self.project / name).read_text())
        self.assertIn(str(self.root), (self.project / ".aios/native.md").read_text())

    def test_tracked_local_settings_are_not_changed(self):
        subprocess.run(["git", "init", str(self.project)], check=True, capture_output=True)
        path = self.project / ".codex/hooks.json"
        path.parent.mkdir()
        path.write_text("{}")
        subprocess.run(["git", "-c", "safe.directory=" + str(self.project), "-C", str(self.project),
                        "add", ".codex/hooks.json"], check=True, capture_output=True)
        self.install(expected=2)
        self.assertEqual(path.read_text(), "{}")
        self.assertFalse(self.root.exists())

    def test_concurrent_close_retains_both_project_rows(self):
        self.install()
        a, b = self.start(native="parallel-a"), self.start(native="parallel-b")
        paths = [self.request("close", activation=sid, summary="Parallel fixture", relaunch="no")[1]
                 for sid in (a, b)]
        processes = [subprocess.Popen([sys.executable, "-I", "-B", str(self.root / "runtime/aios.py"),
                                       "--request", str(path)], stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True) for path in paths]
        for proc in processes:
            out, err = proc.communicate(timeout=35)
            self.assertEqual(proc.returncode, 0, out + err)
            self.assertEqual(json.loads(out)["status"], "closed")
        self.submit("reconcile")
        rows = list(csv.DictReader(io.StringIO((self.project / "interaction-log.csv").read_text())))
        self.assertEqual({row["session_id"] for row in rows}, {a, b})
        self.assertEqual(len(rows), 2)

if __name__ == "__main__":
    unittest.main()
