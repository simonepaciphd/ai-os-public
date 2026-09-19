"""Admission recovery and alias reads; disposable state, no provider calls."""
import errno
import json
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

import test_close_recovery as lifecycle
from test_shared_read import exclusive_handle
from aios_native.bookkeeping import digest
from aios_native.ingress import hook_request


class MissingActivationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = lifecycle.CloseRecoveryTests('test_close_verification')
        self.fixture.setUp()
        self.bk = self.fixture.bk
        self.alias = self.bk.root/'aliases'/(digest(b'claude-code:fixture-native')+'.json')

    def tearDown(self):
        self.fixture.tearDown()

    def test_missing_prompt_explains_real_recovery(self):
        self.fixture.payload['session_id'] = 'never-admitted'
        for _ in range(2):
            code, result, err = self.fixture.cli(event='UserPromptSubmit')
            self.assertEqual(code, 0)
            self.assertFalse(result['continue'])
            reason = result['stopReason']
            self.assertIn('native-activation-missing', reason)
            self.assertIn('SessionStart', reason)
            self.assertIn('Restart or resume', reason)
            self.assertIn('Retrying the prompt', reason)
            self.assertNotIn('Submit the existing reconcile request', reason)
            self.assertNotIn('then an explicit resume', reason)
            self.assertNotIn('never-admitted', err)
        unknown = self.bk.root/'aliases'/(digest(b'claude-code:never-admitted')+'.json')
        self.assertFalse(unknown.exists())

    def test_native_start_recovers_without_task_execution(self):
        self.fixture.payload['session_id'] = 'never-admitted'
        self.fixture.cli(event='UserPromptSubmit')
        _, result, _ = self.fixture.cli(event='SessionStart')
        receipt = json.loads(result['hookSpecificOutput']['additionalContext'])['aios']
        self.assertEqual(receipt['status'], 'active')
        self.assertEqual(receipt['claims'], [])
        _, result, _ = self.fixture.cli(event='UserPromptSubmit')
        next_receipt = json.loads(result['hookSpecificOutput']['additionalContext'])['aios']
        self.assertEqual(receipt['activation'], next_receipt['activation'])
        self.assertEqual(self.bk._session(receipt['activation'])['task'], 'Awaiting agent scope')

    def test_non_start_events_never_admit(self):
        self.fixture.payload['session_id'] = 'never-admitted'
        for event in ('PreToolUse', 'PostToolUse', 'Stop', 'SessionEnd'):
            _, result, _ = self.fixture.cli(event=event)
            self.assertFalse(result['continue'])
        unknown = self.bk.root/'aliases'/(digest(b'claude-code:never-admitted')+'.json')
        self.assertFalse(unknown.exists())

    def test_false_exists_result_cannot_hide_current_alias(self):
        original = Path.exists
        def exists(path, *args, **kwargs):
            return False if path == self.alias else original(path, *args, **kwargs)
        with patch.object(Path, 'exists', exists):
            req = hook_request(self.bk, {**self.fixture.payload, 'hook_event_name':'UserPromptSubmit'}, 'claude-code')
        self.assertEqual(req['activation'], self.fixture.sid)
        self.assertEqual(req['operation'], 'checkpoint')

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing')
    def test_transient_alias_lock_recovers_prompt(self):
        _, close = exclusive_handle(self.alias)
        timer = threading.Timer(.05, close)
        timer.start()
        try:
            code, result, err = self.fixture.cli(event='UserPromptSubmit')
        finally:
            timer.join()
            close()
        self.assertEqual((code, err), (0, ''))
        receipt = json.loads(result['hookSpecificOutput']['additionalContext'])['aios']
        self.assertEqual(receipt['activation'], self.fixture.sid)

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing')
    def test_persistent_alias_lock_stays_permission_error(self):
        before = self.alias.read_bytes()
        _, close = exclusive_handle(self.alias)
        try:
            code, result, _ = self.fixture.cli(event='UserPromptSubmit')
        finally:
            close()
        self.assertEqual(code, 0)
        self.assertFalse(result['continue'])
        self.assertIn('permission-denied', result['stopReason'])
        self.assertNotIn('native-activation-missing', result['stopReason'])
        self.assertEqual(before, self.alias.read_bytes())

    def test_read_disappearance_classified_as_missing(self):
        original = Path.read_bytes
        def read(path):
            if path == self.alias:
                raise FileNotFoundError(errno.ENOENT, 'fixture')
            return original(path)
        with patch.object(Path, 'read_bytes', read):
            _, result, _ = self.fixture.cli(event='UserPromptSubmit')
        self.assertIn('native-activation-missing', result['stopReason'])

    def test_corrupt_alias_is_not_fresh_admission(self):
        for body in (b'{broken', b'{}', b'[]', b'{"activation":null}', b'{"activation":""}'):
            self.alias.write_bytes(body)
            _, result, _ = self.fixture.cli(event='SessionStart')
            self.assertFalse(result['continue'])
            self.assertNotIn('native-activation-missing', result['stopReason'])
            self.assertEqual(self.alias.read_bytes(), body)

    def test_terminal_prompt_never_reopens(self):
        self.fixture.close()
        _, result, _ = self.fixture.cli(event='UserPromptSubmit')
        self.assertFalse(result['continue'])
        self.assertIn('already closed', result['stopReason'])
        self.assertEqual(self.bk._session(self.fixture.sid)['status'], 'done')


if __name__ == '__main__':
    unittest.main()
