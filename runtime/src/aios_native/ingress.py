"""Native hook adapter and semantic-input CLI. Never reads provider transcripts."""
from __future__ import annotations
import argparse
from datetime import datetime
import json
import math
import os
import re
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
    # Read directly: exists() suppresses access errors and can misclassify an
    # unreadable binding as missing admission. Reuse the bounded Windows read
    # retry; only a genuinely absent alias is an unadmitted conversation.
    from .sharded import shared_read
    try:
        alias_bytes = shared_read(alias)
    except FileNotFoundError:
        activation = None
    else:
        binding = json.loads(alias_bytes)
        if (not isinstance(binding, dict) or not isinstance(binding.get("activation"), str)
                or not re.fullmatch(r"[A-Za-z0-9-]{1,120}", binding["activation"])):
            raise Refused("invalid-activation")
        activation = binding["activation"]
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


def registration_command(bk, payload, project='PROJECT_SLUG', kind='REGISTRATION_KIND', *, describe=False):
    """Literal portable CLI invocation; no shell fragments or alternate config."""
    launcher = (bk.os_root/'runtime/aios.py').as_posix()
    interpreter = Path(sys.executable).as_posix()
    cwd = Path(payload['cwd']).resolve().as_posix()
    native = payload['session_id']
    # One spelling accepted by Bash and (on Windows) PowerShell. Refuse paths
    # requiring shell expansion rather than widening the registration gate.
    if (not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', native)
            or any(c in interpreter+launcher+cwd for c in "'\r\n\0\"`$!%&|<>^")):
        raise Refused('registration-command-identity-unsupported')
    prefix = 'powershell.exe -NoProfile -Command "& ' if os.name == 'nt' else ''
    suffix = '"' if os.name == 'nt' else ''
    base = prefix + "'"+interpreter+"' -I -B '"+launcher+"'"
    if describe:
        return base + ' --describe' + suffix
    return (base + " --register-cwd --harness claude-code --native-id "+native+" --workspace '"+cwd+
            "' --project "+project+" --registration-kind "+kind+suffix)


def registration_prompt(bk, payload):
    """Unadmitted conversation only: ask a question, or explicitly register.

    Inspect only the tool name and exact command for this narrow local gate.
    Never retain prompt, question/answer, command or transcript bodies in state.
    """
    from .registration import identity
    bk.ownership()
    if bk.control() != 'clear' or bk.config.get('recovery_only'):
        raise Refused('cleanup-only')
    caller = identity(bk, {'workspace':payload['cwd'], 'native_id':payload['session_id'], 'harness':'claude-code'})
    if caller is not None:
        raise Refused('native-cwd-not-selected')  # A lost existing mapping needs operator repair.
    command = registration_command(bk, payload)
    ending = '"' if os.name == 'nt' else ''
    describe = registration_command(bk, payload, describe=True)
    context = json.dumps({
        'aios': {'status':'registration-required', 'classification':'native-cwd-not-selected',
                 'admitted':False, 'effects':False, 'publication':'not-attempted'},
        'directory':str(Path(payload['cwd']).resolve()),
        'existing_projects':sorted(s for s,v in bk.config['projects'].items() if v.get('provenance',True)),
        'instruction': ('Before the requested work, ask the user which existing project this directory belongs to, '
            'or whether to register it as a new project. If the current user instruction already explicitly names '
            'the project and authorizes registration, use that answer without asking again. Do not infer consent '
            'from the folder name. You may ask in plain text or with AskUserQuestion. Ordinary tools remain blocked. '
            'After an explicit answer, use the exact registration command below with the chosen project slug and '
            'REGISTRATION_KIND replaced by existing or new. Existing adds only a workspace alias, retaining the '
            'canonical project root; new registers this directory as a new project. Do not prepend cd, create a '
            'request file, read a transcript or change settings. Verify configuration, public publication and actual '
            'admission from the command result; then perform mandatory startup reads before ordinary work. '
            'If declined, end the turn. An unregistered conversation has no activation to close. '
            'The exact read_only_diagnostic_command is also available if registration fails. '
            'Do not reconcile/resume to repair missing registration.'),
        'registration_command':command,
        'read_only_diagnostic_command':describe,
    }, sort_keys=True)
    event = payload['hook_event_name']
    if event in {'SessionStart','UserPromptSubmit'}:
        return {'hookSpecificOutput':{'hookEventName':event, 'additionalContext':context}}
    if event == 'PreToolUse':
        tool = payload.get('tool_name')
        inputs = payload.get('tool_input')
        allowed = tool == 'AskUserQuestion'
        if tool in {'Bash','PowerShell'} and isinstance(inputs,dict) and not inputs.get('run_in_background'):
            prefix = command.removesuffix(' --project PROJECT_SLUG --registration-kind REGISTRATION_KIND'+ending)
            pattern = re.escape(prefix+' --project ') + r'[a-z0-9]+(?:-[a-z0-9]+)*'
            pattern += re.escape(' --registration-kind ') + r'(?:existing|new)' + re.escape(ending)
            allowed = isinstance(inputs.get('command'),str) and (inputs['command']==describe or re.fullmatch(pattern, inputs['command']) is not None)
        if allowed:
            return {}  # Preserve ordinary host permissions; never auto-approve.
        return {'hookSpecificOutput':{'hookEventName':event, 'permissionDecision':'deny',
            'permissionDecisionReason':'Directory registration is required. Ask which project it belongs to; only the exact registration command, read-only Describe command or AskUserQuestion is available.',
            'additionalContext':context}}
    # Question completion, failed registration, stop and end do not admit or close.
    return {}


def register_cwd(bk, args):
    """Explicit operator/agent command after the user's project selection.

    Reuse the native preflight, redo journal, claim checks and admission writer.
    A deterministic request key recovers the same operation after interruption.
    """
    from .registration import execute, SLUG
    from .bookkeeping import encoded
    from .sharded import shared_read
    if not SLUG.fullmatch(args.project):
        raise Refused('registration-slug-required')
    existing = bk.config['projects'].get(args.project)
    if args.registration_kind == 'existing' and not existing:
        raise Refused('registration-existing-project-required')
    cwd = str(args.workspace.resolve(strict=True))
    root = str(Path(existing['root']).resolve()) if existing else cwd
    req = {'operation':'register-project', 'phase':'preflight', 'root':root, 'workspace':cwd,
           'native_id':args.native_id, 'harness':args.harness, 'project':args.project}
    if args.registration_kind == 'existing':
        req['attach_workspace'] = True
    req['key'] = 'register-cwd-'+digest(encoded({**req, 'kind':args.registration_kind}))[:40]
    journal = bk.root/'registrations'/(digest(req['key'].encode())+'.json')
    try:
        tx = json.loads(shared_read(journal))
    except FileNotFoundError:
        if args.registration_kind == 'new' and existing:
            raise Refused('registration-slug-conflict')
        validate_request(req)
        preflight = execute(bk,req)
        if preflight.get('conflicts'):
            return preflight
    else:
        preflight = tx['result']
    req.update(phase='apply', preflight=preflight['preflight'])
    validate_request(req)
    return execute(bk, req)


def close_receipt(bk: Bookkeeper, result: dict) -> dict:
    """Observe terminal publication in the closing call; never run task effects.

    This is a bounded readback, not a claim about task correctness or future state.
    Failures retain the committed close and require external bookkeeping recovery.
    """
    verification = {"status": "unconfirmed", "atomic": False}
    try:
        sid = result["activation"]
        state = bk._session(sid)
        active = bk.coord / "sessions" / (sid + ".md")
        closed = bk.coord / "sessions" / "_closed" / (sid + ".md")
        inbox = bk.coord / "mailbox" / "operator"
        notes = [p for p in [inbox / (sid + "-closeout.md"),
                            inbox / "_auto" / (sid + "-closeout.md")] if p.is_file()]
        verification.update(terminal=state["status"] == "done",
            claims_released=state["claims"] == [], active_record_absent=not active.exists(),
            closed_record_matches=closed.read_bytes() == bk._session_bytes(state),
            closeout_present=len(notes) == 1,
            publication_complete=(result.get("publication", "complete") == "complete"
                                  and not state.get("publication_pending", False)))
        if len(notes) == 1:
            verification["closeout_sha256"] = digest(notes[0].read_bytes())
        checks = ("terminal", "claims_released", "active_record_absent", "closed_record_matches",
                  "closeout_present", "publication_complete")
        if all(verification[k] for k in checks):
            verification["status"] = "verified"
    except (OSError, ValueError, KeyError, TypeError, Refused):
        pass  # Never turn a committed close into an instruction to replay work.
    action = ("Close and publication verified in this call. Send the final response with no further tool calls. "
              "To work again, use a fresh native SessionStart; never resume this terminal activation."
              if verification["status"] == "verified" else
              "Close is committed but publication readback is unconfirmed. Make no further tool calls in this activation. "
              "An operator must inspect/reconcile bookkeeping outside this closed activation; never replay task effects. "
              "New work requires a fresh native SessionStart.")
    return {**result, "close_verification": verification, "next_action": action}


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


def validate_registration_argv(argv):
    """Bind registration to argv before configuration/control decisions.

    No hook stdin is read. Reject ambiguity instead of argparse's last-value wins.
    The public launcher has no separate maintenance policy: ownership, shutdown
    and recovery_only are checked by the existing registration writer.
    """
    fields = {'--config', '--harness', '--native-id', '--workspace', '--project', '--registration-kind'}
    permitted = fields | {'--expected-contract'}
    values = {}
    seen = False
    position = 0
    while position < len(argv):
        flag = argv[position]
        if flag == '--register-cwd':
            if seen:
                raise RequestInvalid('invalid-registration-invocation')
            seen = True
            position += 1
            continue
        if flag not in permitted or flag in values or position + 1 >= len(argv):
            raise RequestInvalid('invalid-registration-invocation')
        value = argv[position + 1]
        if not value or value.startswith('--'):
            raise RequestInvalid('invalid-registration-invocation')
        values[flag] = value
        position += 2
    if (not seen or not fields <= values.keys()
            or values['--harness'] not in {'claude-code', 'codex-cli'}
            or values['--registration-kind'] not in {'existing', 'new'}):
        raise RequestInvalid('invalid-registration-invocation')
    return {'operation': 'register-project', 'native_id': values['--native-id'],
            'cwd': values['--workspace'], 'project': values['--project']}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--register-cwd' in argv:
        try:
            validate_registration_argv(argv)
        except RequestInvalid as exc:
            print(json.dumps({'continue': False, 'classification': exc.classification,
                              'stage': 'registration-envelope', 'error_class': type(exc).__name__,
                              'publication': 'not-attempted'}))
            return 2
    parser = argparse.ArgumentParser(allow_abbrev=False, description="Native bookkeeping semantic entrypoint; --describe needs no private config")
    parser.add_argument("--describe", action="store_true", help="print operation schemas, examples and loaded package fingerprints; no effects")
    parser.add_argument("--validate", action="store_true", help="pure request-shape validation; no config, journal or effects")
    parser.add_argument("--expected-contract")
    parser.add_argument("--register-cwd", action="store_true")
    parser.add_argument("--project")
    parser.add_argument("--registration-kind", choices=["existing", "new"])
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
        if any((args.config, args.request, args.harness, args.close_activation, args.close_reason, args.validate, args.intake, args.register_cwd, args.project, args.registration_kind, args.native_id, args.workspace)):
            parser.error("--describe must be used alone")
        package = Path(__file__).resolve().parent
        print(json.dumps({"contract_version": VERSION, "schema": schema(), "examples": examples(),
            "entrypoint": str(package.parents[1] / "aios.py"),
            "source_sha256": {p.name: digest(p.read_bytes()) for p in sorted(package.glob("*.py"))},
            "installation_status": "Source contract only; verify selected installation separately"}, sort_keys=True))
        return 0
    if args.validate:
        try:
            if not args.request or any((args.config,args.harness,args.close_activation,args.intake,args.register_cwd,args.project,args.registration_kind)):
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
        if args.harness and not args.request and not args.close_activation and not args.intake and not args.register_cwd:
            stage = "hook-input-read"
            payload=json.load(sys.stdin)
            if not isinstance(payload,dict): raise RequestInvalid("invalid-request-object")
            event=payload.get("hook_event_name")
            if event_contract(args.harness,event)=='unsupported':
                stage='native-routing'
                raise Refused('unsupported-native-event')
        if args.expected_contract and args.expected_contract != VERSION:
            raise Refused('contract-version-mismatch')
        stage = "configuration"
        bk = Bookkeeper(args.config)
        if args.register_cwd:
            stage = 'registration'
            if (not args.harness or not args.native_id or not args.workspace or not args.project
                    or not args.registration_kind or args.request or args.intake or args.close_activation):
                raise Refused('invalid-registration-invocation')
            result = register_cwd(bk, args)
            print(json.dumps(result, sort_keys=True))
            return 2 if result.get('conflicts') else 0
        if args.intake:
            from .startup_intake import collect
            stage = "intake"
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
            try:
                request = hook_request(bk, payload, args.harness)
            except Refused as exc:
                if str(exc) != 'native-cwd-not-selected' or args.harness != 'claude-code':
                    raise
                output = registration_prompt(bk, payload)
                print(json.dumps(output, sort_keys=True))
                return 0
        stage = "bookkeeping"
        if isinstance(request,dict) and request.get('operation') == 'register-project':
            validate_request(request)
            from .registration import execute as register_project
            stage = 'registration'
            result = register_project(bk, request)
            print(json.dumps(result, sort_keys=True))
            return 2 if result.get('conflicts') else 0
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
            context = json.dumps({"aios": result,"native_command":{"launcher":str(bk.os_root / "runtime" / "aios.py"),"interpreter":sys.executable,"contract_version":VERSION,"close_workflow":"Finish edits, logs and checks before close. Submit close as the final tool call; its close_verification is the publication readback. After a verified close, send the final response without more tools. Closed activations require fresh native SessionStart."}}, sort_keys=True)
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
        if request is not None and request.get("operation") == "close" and result.get("status") == "closed":
            result = close_receipt(bk, result)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, WriterBusy, OSError, ValueError, KeyError, TypeError) as exc:
        if args.register_cwd and stage == 'configuration':
            print(json.dumps({'continue': False, 'classification': 'configuration-unavailable',
                'stage': stage, 'error_class': type(exc).__name__, 'publication': 'not-attempted',
                'action': 'Inspect the selected installation configuration; registration was not attempted.'}))
            return 2
        if stage == 'registration':
            # All refusal messages are code-owned classifications, never bodies.
            code = str(exc).split(':',1)[0] if isinstance(exc,Refused) else type(exc).__name__
            print(json.dumps({'continue':False,'classification':code,'stage':stage,'error_class':type(exc).__name__,
                'publication':'unknown; inspect same registration key',
                'action':'Correct conflicts; repeat preflight if nothing was applied. Retry the exact apply request to recover a prepared publication; never replay research work.'}))
            return 2
        if args.intake and isinstance(exc,Refused) and str(exc) == 'native-not-yet-admitted':
            print(json.dumps({'read_only':True,'admission':'not-yet-admitted','effects':False,
                'classification':'native-not-yet-admitted','publication':'not-attempted',
                'action':'No admission alias exists for this conversation. Register the existing project if mapping is missing; otherwise use explicit native admission with the actual conversation id and cwd. This result does not diagnose deployment failure.'}))
            return 2
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
