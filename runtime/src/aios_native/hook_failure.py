"""Safe event-specific failure output; never retries a task or claims unknown effects."""
from datetime import datetime,timezone
import json
import uuid
from aios_core.store import WriterBusy
from .bookkeeping import Refused
from .request_contract import RequestInvalid,VERSION

EVENTS={'SessionStart','UserPromptSubmit','PreToolUse','PostToolUse','PostToolUseFailure','SessionEnd','Stop','Interrupt'}
CLAUDE_DECISION_EVENTS=EVENTS-{'SessionEnd','Interrupt'}
HARNESS_EVENTS={'codex-cli':EVENTS,'claude-code':CLAUDE_DECISION_EVENTS|{'SessionEnd'}}

def event_contract(harness,event):
    if not isinstance(event,str) or event not in HARNESS_EVENTS.get(harness,set()):
        return 'unsupported'
    if harness=='claude-code':
        return 'stderr-termination' if event=='SessionEnd' else 'structured-stop'
    return 'codex-native'
SAFE_CODES={'ownership-changed','integration-disabled','cleanup-only','claim-overlap',
 'activation-closed','activation-missing','explicit-activation-required','native-identity-missing',
 'native-activation-missing','native-cwd-not-selected','native-project-changed','ambiguous-native-cwd',
 'unsupported-native-event','publication-conflict','conflicting-duplicate','invalid-mode',
 'invalid-close-invocation','activation-still-live','harness-required','invalid-activation','contract-version-mismatch'}

def failure(exc,stage,event,harness,metadata):
    code=('native-writer-busy' if isinstance(exc,WriterBusy) else
          'invalid-request' if isinstance(exc,RequestInvalid) else
          'permission-denied' if isinstance(exc,PermissionError) else
          'io-publication-error' if isinstance(exc,OSError) and stage=='bookkeeping' else
          'io-read-error' if isinstance(exc,OSError) else 'invalid-input')
    if isinstance(exc,Refused) and not isinstance(exc,RequestInvalid):
        prefix=str(exc).split(':',1)[0]
        code=prefix if prefix in SAFE_CODES else 'bookkeeping-refused'
    transport=event_contract(harness,event)
    event=event if isinstance(event,str) and event in EVENTS else 'unknown-or-unsupported'
    if transport=='unsupported' and harness is not None: code='unsupported-native-event'
    publication='unknown' if stage in {'bookkeeping','controls'} else 'not-attempted'
    if isinstance(exc,WriterBusy):
        publication='not-attempted' if metadata.get('writer_phase')=='lock-wait' else 'unknown'
    if isinstance(exc,RequestInvalid): publication='not-attempted'
    diagnostic=dict(metadata)
    diagnostic.update(version='native-hook-failure-v1',event=event,observed_at=datetime.now(timezone.utc).isoformat(),
        correlation_id=uuid.uuid4().hex,classification=code,stage=stage,publication=publication,
        tool_call='succeeded' if event=='PostToolUse' else 'failed' if event=='PostToolUseFailure' else 'unknown',
        task_effect='unknown')
    code_out=0 if transport=='structured-stop' else 2
    diagnostic.update(hook_identity='aios-native-ingress',contract_version=VERSION,exit_status=code_out,
        transport=transport,event_supported=transport!='unsupported')
    # Event identity proves a returned call, never background-job completion.
    prefix=('Tool call returned successfully; background/task completion remains unknown. ' if event=='PostToolUse' else
            'Tool call failed; partial task effects remain unknown. ' if event=='PostToolUseFailure' else '')
    recovery=('Use the installed runtime/aios.py --describe; inspect the existing task result/status. '
        'Submit the existing reconcile request for bookkeeping only, then an explicit resume with the fresh current activation. '
        'A closed activation requires native SessionStart; never replay a completed task effect or guess an activation.')
    disposition=('Session termination cannot be paused by this hook; close is unconfirmed. ' if transport=='stderr-termination' else
        'Unsupported delivery; no host stop or close is confirmed. ' if transport=='unsupported' else
        'Stop requested; actual host enforcement is not attested. ')
    message=prefix+'AI OS bookkeeping failed ['+code+']; publication '+publication+'. '+disposition+recovery+' Diagnostic: '+json.dumps(diagnostic,sort_keys=True)
    output={'continue':False,'stopReason':message}
    if event=='PreToolUse':
        output['hookSpecificOutput']={'hookEventName':event,'permissionDecision':'deny','permissionDecisionReason':message}
    if isinstance(exc,RequestInvalid):
        output['request_error']={'classification':exc.classification,'field':exc.field,'action':'Use --describe; supply the fresh current activation where required'}
    # Claude consumes structured JSON decisions on exit 0. Exit 2 uses stderr
    # and does not implement the same stop semantics. SessionEnd cannot gate.
    return output,message,code_out
