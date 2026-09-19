"""Disposable close lifecycle fixtures. No provider or live state."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'runtime/src'))
from aios_native.bookkeeping import Bookkeeper, Refused, encoded
from aios_native.ingress import hook_request, main

class CloseRecoveryTests(unittest.TestCase):
    sharded = True
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.osroot = self.base/'os'
        self.project = self.base/'project'
        self.config = self.base/'ownership.json'
        for p in [self.project, self.osroot/'coord/control', self.osroot/'coord/sessions', self.osroot/'coord/mailbox', self.osroot/'coord/inbox']:
            p.mkdir(parents=True)
        (self.osroot/'coord/SPEC.md').write_text('budgets: claude-code=4, codex-cli=4\n')
        doc = dict(enabled=True, owner='v2', epoch='fixture', mode='rehearsal', rehearsal_root=str(self.base), os_root=str(self.osroot), state_root=str(self.base/'state'), projects={'sample': dict(root=str(self.project), provenance=False, worktrees=[])})
        if self.sharded:
            doc.update(mode='rehearsal-sharded', storage_format='project-session-v1', storage_generation='fixture')
        self.config.write_bytes(encoded(doc))
        self.bk = Bookkeeper(self.config)
        self.payload = dict(hook_event_name='SessionStart', session_id='fixture-native', cwd=str(self.project))
        self.sid = self.bk.execute(hook_request(self.bk, self.payload, 'claude-code'))['activation']
    def tearDown(self):
        assert self.base.parent == Path(tempfile.gettempdir()).resolve()
        if os.name == 'nt': self.tmp.name = '\\\\?\\' + str(self.base)
        self.tmp.cleanup()
    def cli(self, request=None, event=None):
        args = ['--config', str(self.config)]
        if request is not None:
            path = self.base/'request.json'
            path.write_bytes(encoded(request))
            args += ['--request', str(path)]
        else: args += ['--harness', 'claude-code']
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), patch('sys.stdin', io.StringIO(json.dumps({**self.payload, 'hook_event_name': event}))):
            code = main(args)
        return code, json.loads(out.getvalue()), err.getvalue()
    def close(self):
        return self.cli(dict(operation='close', key='fixture-close', activation=self.sid, summary='Fixture completed'))
    def test_close_verification(self):
        code, result, _ = self.close()
        self.assertEqual(code, 0)
        self.assertEqual(result['close_verification']['status'], 'verified')
        self.assertTrue(result['close_verification']['claims_released'])
        self.assertIn('no further tool calls', result['next_action'])
    def test_duplicate_close(self):
        self.close()
        note = self.osroot/'coord/mailbox/operator'/f'{self.sid}-closeout.md'
        before = note.read_bytes()
        _, result, _ = self.close()
        self.assertTrue(result['duplicate'])
        self.assertEqual(result['close_verification']['status'], 'verified')
        self.assertEqual(before, note.read_bytes())
    def test_terminal_refusal_guidance(self):
        self.close()
        code, result, _ = self.cli(event='PreToolUse')
        self.assertEqual(code, 0)
        self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny')
        self.assertIn('already closed', result['stopReason'])
        self.assertNotIn('Submit the existing reconcile request', result['stopReason'])
        self.assertNotIn('then an explicit resume', result['stopReason'])
        self.assertIn('SessionStart', result['stopReason'])
        self.assertEqual(self.bk._session(self.sid)['status'], 'done')
    def test_late_events_inert_prompt_refused(self):
        self.close()
        for event in ['PostToolUse', 'PostToolUseFailure', 'Stop', 'SessionEnd']:
            self.assertIsNone(hook_request(self.bk, {**self.payload, 'hook_event_name': event}, 'claude-code'))
        with self.assertRaises(Refused):
            hook_request(self.bk, {**self.payload, 'hook_event_name': 'UserPromptSubmit'}, 'claude-code')
    def test_fresh_sessionstart(self):
        self.close()
        req = hook_request(self.bk, self.payload, 'claude-code')
        result = self.bk.execute(req)
        self.assertNotEqual(result['activation'], self.sid)
        self.assertEqual(result['claims'], [])
        self.assertEqual(self.bk._session(self.sid)['status'], 'done')
    def test_prompt_teaches_close_order(self):
        _, result, _ = self.cli(event='UserPromptSubmit')
        context = json.loads(result['hookSpecificOutput']['additionalContext'])
        self.assertIn('final tool call', context['native_command']['close_workflow'])
    def test_pending_not_verified(self):
        if not self.sharded: self.skipTest('sharded outbox only')
        with patch('aios_native.sharded.ProjectBookkeeper._flush_close', return_value='pending'):
            _, result, _ = self.close()
        self.assertEqual(result['publication'], 'pending')
        self.assertEqual(result['close_verification']['status'], 'unconfirmed')
        self.assertIn('outside this closed activation', result['next_action'])
    def test_missing_projection_not_verified(self):
        self.close()
        (self.osroot/'coord/sessions/_closed'/f'{self.sid}.md').unlink()
        _, result, _ = self.close()
        self.assertEqual(result['close_verification']['status'], 'unconfirmed')

class LegacyCloseRecoveryTests(CloseRecoveryTests):
    sharded = False

if __name__ == '__main__': unittest.main()
