"""Native hook adapter and semantic-input CLI. Never reads provider transcripts."""
from __future__ import annotations
import argparse
from datetime import datetime
import json
import math
import sys
import uuid
from pathlib import Path
from aios_core.store import WriterBusy
from .bookkeeping import Bookkeeper, Refused, digest, workspace_matches, PUBLICATION_ROLES
from .request_contract import RequestInvalid, VERSION, schema, examples, validate_request
from .hook_failure import failure, HARNESS_EVENTS, event_contract

EVENTS = {"SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse",
          "PostToolUseFailure", "SessionEnd", "Stop", "Interrupt"}

def hook_request(bk: Bookkeeper, payload: dict, harness: str) -> dict | None:
    event = payload.get("hook_event_name")
    if not isinstance(event,str) or event not in HARNESS_EVENTS.get(harness,set()):
        raise Refused("unsupported-native-event")
    native = payload.get("session_id")
    cwd = payload.get("cwd")
    if not isinstance(native, str) or not isinstance(cwd, str):
        raise Refused("native-identity-missing")
    candidates = []
    for slug, value in bk.config["projects"].items():
        for root in [value["root"]] + value.get("worktrees", []):
            base = Path(root).resolve()
            if workspace_matches(value, Path(cwd), base):
                candidates.append((len(base.parts), slug, value))
    if not candidates:
        raise Refused("native-cwd-not-selected")
    depth = max(x[0] for x in candidates)
    matching = [(slug, value) for n, slug, value in candidates if n == depth]
    if len(matching) != 1:
        raise Refused("ambiguous-native-cwd")
    alias = bk.root / "aliases" / (digest((harness + ":" + native).encode()) + ".json")
    activation = json.loads(alias.read_bytes())["activation"] if alias.exists() else None
    key = "native-" + uuid.uuid4().hex
    if activation:
        state = bk._session(activation)
        if state["status"] != "active":
            if event == "SessionStart":
                # Explicit native start/resume creates a NEW activation; old one remains terminal.
                return {"operation": "activate", "key": "native-reactivate-" + activation,
                        "project": matching[0][0], "native_id": native, "harness": harness,
                        "model": payload.get("model", "unavailable"), "tab": "AIOS WORK",
                        "worktree": cwd}
            if event in {"SessionEnd", "Stop", "PostToolUse", "PostToolUseFailure", "Interrupt"}:
                return None
            raise Refused("explicit-activation-required:" + native)
        if state["project"] != matching[0][0]:
            raise Refused("native-project-changed")
        if event == "SessionEnd" or bk.control() != "clear":
            return {"operation": "close", "key": "native-close-" + activation,
                    "activation": activation}
        # A new prompt is an explicit return to work. Reuse the writer's
        # resume checks after idle instead of rejecting the prompt checkpoint.
        # Tool/status deliveries cannot renew stale authority on their own.
        idle_prompt = (event == "UserPromptSubmit" and
                       (bk.clock() - datetime.fromisoformat(state["heartbeat"])).total_seconds() > 3600)
        return {"operation": "resume" if event == "SessionStart" or idle_prompt else "checkpoint",
                "key": key, "activation": activation, "worktree": cwd}
    if event != "SessionStart":
        raise Refused("native-activation-missing")
    return {"operation": "start", "key": "native-start-" + bk.config["epoch"] + "-" +
            digest((harness + ":" + native).encode()),
            "project": matching[0][0], "native_id": native, "harness": harness,
            "model": payload.get("model", "unavailable"), "tab": "AIOS WORK", "worktree": cwd}

def failure_metadata(exc: Exception, stage: str) -> dict:
    """No payloads, exception messages, paths or transcript content in diagnostics."""
    result = {"error_class": type(exc).__name__, "stage": stage}
    if isinstance(exc, WriterBusy):
        phase = getattr(exc, "native_writer_phase", None)
        if isinstance(phase, str) and phase in {"lock-wait", "reconciliation", "planning", "publication"}:
            result["writer_phase"] = phase
        for name in ("lock_wait_ms", "lock_held_ms"):
            value = getattr(exc, "native_" + name, None)
            if type(value) in {int, float} and math.isfinite(value) and value >= 0:
                result[name] = round(value, 3)
    role = getattr(exc, "native_publication_role", None)
    if isinstance(role, str) and role in PUBLICATION_ROLES:
        result["publication_role"] = role
    attempts = getattr(exc, "native_publication_attempts", None)
    if type(attempts) is int and attempts >= 1:
        result["publication_attempts"] = attempts
    elapsed = getattr(exc, "native_publication_elapsed_ms", None)
    if type(elapsed) in {int, float} and math.isfinite(elapsed) and elapsed >= 0:
        result["publication_elapsed_ms"] = round(elapsed, 3)
    for field in ("errno", "winerror"):
        value = getattr(exc, field, None)
        if isinstance(value, int):
            result[field] = value
    for field in ("filename", "filename2"):
        value = getattr(exc, field, None)
        if isinstance(value, (str, bytes)):
            raw = value.encode("utf-8", errors="replace") if isinstance(value, str) else value
            result[field + "_sha256"] = digest(raw)
    tb = exc.__traceback__
    # Only this package's source coordinates; no locals or arbitrary caller names.
    package = Path(__file__).resolve().parent
    while tb is not None:
        frame = tb.tb_frame
        if Path(frame.f_code.co_filename).resolve().parent == package:
            result["site"] = Path(frame.f_code.co_filename).name + ":" + str(tb.tb_lineno)
        tb = tb.tb_next
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Native bookkeeping semantic entrypoint; --describe needs no private config")
    parser.add_argument("--describe", action="store_true", help="print operation schemas, examples and loaded package fingerprints; no effects")
    parser.add_argument("--validate", action="store_true", help="pure request-shape validation; no config, journal or effects")
    parser.add_argument("--expected-contract")
    parser.add_argument("--intake", action="store_true")
    parser.add_argument("--native-id")
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--recipient", default="operator")
    parser.add_argument("--page-size", type=int, default=32)
    parser.add_argument("--cursor")
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--harness", choices=["codex-cli", "claude-code"])
    parser.add_argument("--request", type=Path)
    parser.add_argument("--close-activation")
    parser.add_argument("--close-reason", choices=["stale-sweep", "shutdown-deadline"])
    args = parser.parse_args(argv)
    if args.expected_contract and args.expected_contract != VERSION and not args.harness:
        print(json.dumps({"continue":False,"stopReason":"AI OS: selected contract version mismatch; consult approved deployment inventory"}))
        return 0 if args.harness=='claude-code' else 2
    if args.describe:
        if any((args.config, args.request, args.harness, args.close_activation, args.close_reason, args.validate, args.intake)):
            parser.error("--describe must be used alone")
        package = Path(__file__).resolve().parent
        print(json.dumps({"contract_version": VERSION, "schema": schema(), "examples": examples(),
            "entrypoint": str(package.parents[1] / "bin" / "aios-native.py"),
            "source_sha256": {p.name: digest(p.read_bytes()) for p in sorted(package.glob("*.py"))},
            "installation_status": "Source contract only; verify selected installation separately"}, sort_keys=True))
        return 0
    if args.validate:
        try:
            if not args.request or any((args.config,args.harness,args.close_activation,args.intake)):
                raise RequestInvalid("invalid-request-object")
            validate_request(json.loads(args.request.read_text(encoding="utf-8-sig")))
            print(json.dumps({"valid_request_shape":True,"contract_version":VERSION,"effects":False,"current_authority_checked":False}))
            return 0
        except (Refused, OSError, ValueError, TypeError, KeyError) as exc:
            output,message,code=failure(exc,"request",None,None,failure_metadata(exc,"request"))
            print(json.dumps(output));print(message,file=sys.stderr);return code
    if args.config is None:
        parser.error("--config is required for bookkeeping; use --describe for the contract")
    event = None
    request = None
    stage = "configuration"
    try:
        # Parse only the event envelope before opening config so failures retain
        # event-specific semantics. Never persist prompt/tool/transcript fields.
        payload = None
        if args.harness and not args.request and not args.close_activation and not args.intake:
            payload=json.load(sys.stdin)
            if not isinstance(payload,dict): raise RequestInvalid("invalid-request-object")
            event=payload.get("hook_event_name")
            if event_contract(args.harness,event)=='unsupported':
                stage='native-routing'
                raise Refused('unsupported-native-event')
        if args.expected_contract and args.expected_contract != VERSION:
            raise Refused('contract-version-mismatch')
        bk = Bookkeeper(args.config)
        if args.intake:
            from .startup_intake import collect
            if not args.workspace or args.request or args.close_activation:
                raise Refused("invalid-intake-invocation")
            result=collect(bk,native_id=args.native_id,harness=args.harness,cwd=args.workspace,
                recipient=args.recipient,page_size=args.page_size,cursor=args.cursor,history=args.history)
            print(json.dumps(result,sort_keys=True));return 0 if not result['errors'] else 2
        stage = "request"
        if args.close_activation:
            bk._compat_close_reason = args.close_reason
            if not args.close_reason or args.request or args.harness:
                raise Refused("invalid-close-invocation")
            if args.close_reason == "stale-sweep":
                from datetime import datetime
                state = bk._session(args.close_activation)
                age = (bk.clock() - datetime.fromisoformat(state["heartbeat"])).total_seconds()
                if state["status"] == "active" and age <= 3600:
                    raise Refused("activation-still-live")
            request = {"operation": "close", "activation": args.close_activation,
                       "key": "compat-close-" + args.close_reason + "-" + args.close_activation,
                       "summary": "PENDING: " + args.close_reason + "; inspect saved work and prior semantic checkpoint",
                       "relaunch": "operator-decides"}
        elif args.request:
            request = json.loads(args.request.read_text(encoding="utf-8-sig"))
        else:
            if not args.harness:
                raise Refused("harness-required")
            stage = "ownership"
            bk.ownership()
            stage = "native-routing"
            request = hook_request(bk, payload, args.harness)
        stage = "bookkeeping"
        # Ordinary hooks have a 30-second native deadline and may arrive in
        # parallel. Preserve the short budget of the 3-second close hooks.
        lock_timeout = 2 if event in {"SessionEnd", "Interrupt"} else 20
        result = (bk.execute(request, lock_timeout_seconds=lock_timeout)
                  if request is not None else {"status": "closed"})
        if (event == "SessionEnd" or args.close_activation) and result.get("publication") == "pending":
            print("{}")
            print("AI OS: native close committed; project publication pending. Reconcile bookkeeping only; never replay task effects.", file=sys.stderr)
            return 2
        stage = "controls"
        stop = bk.control() != "clear"
        if event:
            context = json.dumps({"aios": result,"native_command":{"launcher":str(bk.os_root / "runtime" / "aios.py"),"interpreter":sys.executable,"contract_version":VERSION}}, sort_keys=True)
            if event == "PreToolUse":
                output = {"hookSpecificOutput": {"hookEventName": event,
                          "permissionDecision": "deny",
                          "permissionDecisionReason": "AI OS cleanup-only"}} if stop else {}
            elif event in {"SessionStart", "UserPromptSubmit"}:
                output = {"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}
                if stop:
                    output["continue"] = False
                    output["stopReason"] = "AI OS cleanup-only; bookkeeping closed"
            else:
                output = {}
            if stop:
                output.update({"continue":False,"stopReason":"AI OS cleanup-only; bookkeeping closed. Completed task effects must not be rerun; use the existing shutdown/closeout workflow."})
            print(json.dumps(output))
            return 2 if stop and args.harness!='claude-code' and event in {"PreToolUse", "UserPromptSubmit"} else 0
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, WriterBusy, OSError, ValueError, KeyError, TypeError) as exc:
        if event is None and isinstance(exc,Refused) and str(exc) in {'integration-disabled','ownership-changed','harness-required'}:
            reason='AI OS: '+str(exc)
            print(json.dumps({'continue':False,'stopReason':reason}),flush=True)
            print(reason,file=sys.stderr,flush=True)
            return 2
        if isinstance(exc,RequestInvalid) and event is None:
            # Preserve the accepted semantic CLI contract; richer event-specific
            # stop/recovery output belongs to native hook delivery.
            reason='AI OS: '+str(exc)
            print(json.dumps({'continue':False,'stopReason':reason,'request_error':{
                'classification':exc.classification,'field':exc.field,
                'action':'Use --describe; supply your current activation from a fresh receipt where required'}}),flush=True)
            print(reason,file=sys.stderr,flush=True)
            return 2
        metadata=failure_metadata(exc,stage)
        if isinstance(request,dict) and isinstance(request.get('activation'),str):
            import re
            if re.fullmatch(r'[A-Za-z0-9-]{1,120}',request['activation']): metadata['activation']=request['activation']
        output,message,code=failure(exc,stage,event,args.harness,metadata)
        print(json.dumps(output), flush=True)
        print(message, file=sys.stderr, flush=True)
        return code

if __name__ == "__main__":
    raise SystemExit(main())
