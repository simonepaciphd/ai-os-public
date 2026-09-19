"""Public launcher regressions; synthetic roots, no provider or user settings."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_runtime
import test_registration
from aios_native import ingress
from aios_native.bookkeeping import encoded
from aios_native.registration import ASSETS, LOG, execute


class RegistrationTransportTests(unittest.TestCase):
    setUp = test_runtime.RuntimeTests.setUp
    tearDown = test_runtime.RuntimeTests.tearDown
    install = test_runtime.RuntimeTests.install
    cli = test_runtime.RuntimeTests.cli

    def setup_registration(self):
        self.install()
        self.folder = self.base/'new folder with spaces'
        self.folder.mkdir()
        self.argv = ['--register-cwd', '--harness', 'claude-code', '--native-id', 'new-session',
                     '--workspace', str(self.folder), '--project', 'new-project', '--registration-kind', 'new']

    def run_registration(self, argv=None, stdin=''):
        return subprocess.run([sys.executable, '-I', '-B', str(self.root/'runtime/aios.py'),
                               *(self.argv if argv is None else argv)], input=stdin,
                              capture_output=True, text=True, encoding="utf-8", cwd=self.folder, timeout=35)

    def snapshot(self):
        return {str(p.relative_to(self.base)): p.read_bytes() for p in self.base.rglob('*') if p.is_file()}

    def test_stdin_is_not_registration_identity(self):
        self.setup_registration()
        for body in ('', '{invalid', '\ufeff{}', '{"operation":"close","native_id":"wrong"}',
                     '{"operation":"reconcile","hook_event_name":"SessionEnd"}'):
            run = self.run_registration(stdin=body)
            self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
            result = json.loads(run.stdout)
            self.assertEqual(result['public_publication'], 'verified')
            self.assertEqual(result['admission']['workspace'], str(self.folder))
            self.assertEqual(result['admission']['project'], 'new-project')
        self.assertEqual(len(list(ingress.Bookkeeper(self.config).root.joinpath('activations').glob('*.json'))), 1)

    def test_empty_hook_stdin_keeps_input_diagnostic(self):
        self.setup_registration()
        run = self.run_registration(['--harness','claude-code'], '')
        self.assertEqual(run.returncode,2)
        diagnostic = json.loads(json.loads(run.stdout)['stopReason'].split(' Diagnostic: ',1)[1])
        self.assertEqual(diagnostic['stage'],'hook-input-read')
        self.assertEqual(diagnostic['error_class'],'JSONDecodeError')

    def test_closed_registration_identity_cannot_reopen(self):
        self.setup_registration()
        run = self.run_registration()
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        sid = json.loads(run.stdout)['admission']['activation']
        keeper = ingress.Bookkeeper(self.config)
        keeper.execute({'operation':'close','key':'fixture-close','activation':sid,'summary':'Fixture done'})
        before = self.snapshot()
        run = self.run_registration(stdin='{"operation":"close"}')
        self.assertEqual(run.returncode,2,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['classification'],'explicit-activation-required')
        self.assertEqual(before,self.snapshot())
        self.assertEqual(keeper._session(sid)['status'],'done')

    def test_malformed_argv_has_no_effects(self):
        self.setup_registration()
        before = self.snapshot()
        cases = [self.argv+['--native-id','other'], self.argv+['--register-cwd'],
                 self.argv[:-1], self.argv+['--request','private.json'],
                 self.argv+['--doctor'], self.argv+['--status'], self.argv+['--describe'],
                 self.argv+['--config',str(self.config),'--config',str(self.config)],
                 self.argv+['--unknown','value'], self.argv+['--native','abbreviated']]
        for args in cases:
            with self.subTest(args=args):
                run = self.run_registration(args, '{"operation":"close"}')
                self.assertEqual(run.returncode, 2, run.stdout+run.stderr)
                result = json.loads(run.stdout)
                self.assertEqual(result['stage'], 'registration-envelope')
                self.assertEqual(result['publication'], 'not-attempted')
                self.assertNotIn(str(self.base), run.stdout)
                self.assertEqual(before, self.snapshot())

    def test_hostile_stdin_cannot_bypass_shutdown_or_recovery(self):
        self.setup_registration()
        flag = self.root/'coord/control/SHUTDOWN-REQUESTED.md'
        flag.write_text('fixture shutdown')
        for mode in ('shutdown', 'recovery'):
            if mode == 'recovery':
                flag.unlink()
                config = json.loads(self.config.read_bytes())
                config['recovery_only'] = True
                self.config.write_bytes(encoded(config))
            before = self.snapshot()
            run = self.run_registration(stdin='{"operation":"close","hook_event_name":"SessionEnd"}')
            self.assertEqual(run.returncode, 2, run.stdout+run.stderr)
            self.assertIn('cleanup-only', json.loads(run.stdout)['conflicts'])
            self.assertEqual(before, self.snapshot())

    def test_configuration_diagnostic_differs_from_input(self):
        self.setup_registration()
        self.config.write_text('{broken')
        run = self.run_registration(stdin='not-json')
        self.assertEqual(run.returncode, 2)
        self.assertIn('"stage": "configuration"', run.stdout)
        self.assertIn('JSONDecodeError', run.stdout)
        self.assertNotIn(str(self.base), run.stdout+run.stderr)
        self.config.unlink()
        run = self.run_registration()
        self.assertIn('FileNotFoundError', run.stdout)
        self.assertNotIn(str(self.base), run.stdout+run.stderr)

    def test_generated_registration_and_describe_commands_execute(self):
        self.setup_registration()
        payload = {'hook_event_name':'SessionStart','session_id':'new-session','cwd':str(self.folder)}
        result = self.cli('--harness','claude-code',payload=payload,cwd=self.folder)
        context = json.loads(result['hookSpecificOutput']['additionalContext'])
        diagnostic = context['read_only_diagnostic_command']
        command = context['registration_command'].replace('PROJECT_SLUG','new-project').replace('REGISTRATION_KIND','new')
        before = self.snapshot()
        for candidate in (diagnostic, command):
            gate = self.cli('--harness','claude-code',payload={**payload,'hook_event_name':'PreToolUse',
                'tool_name':'Bash','tool_input':{'command':candidate}},cwd=self.folder)
            self.assertEqual(gate,{})
            run = subprocess.run(candidate, shell=True, stdin=subprocess.DEVNULL, capture_output=True,
                                 text=True,cwd=self.folder,timeout=35)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            if candidate == diagnostic:
                self.assertEqual(json.loads(run.stdout)['contract_version'],'native-semantic-public-1')
                self.assertEqual(before,self.snapshot())
            else:
                self.assertEqual(json.loads(run.stdout)['public_publication'],'verified')

    @unittest.skipUnless(os.name == 'nt', 'Windows PowerShell and Git Bash transport')
    def test_windows_shells_with_closed_stdin(self):
        self.setup_registration()
        bk = ingress.Bookkeeper(self.config)
        command = ingress.registration_command(bk,{'session_id':'new-session','cwd':str(self.folder)},'new-project','new')
        powershell = subprocess.run(['powershell.exe','-NoProfile','-Command',command],
            stdin=subprocess.DEVNULL,capture_output=True,text=True,cwd=self.folder,timeout=35)
        self.assertEqual(powershell.returncode,0,powershell.stdout+powershell.stderr)
        bash = Path('C:/Program Files/Git/bin/bash.exe')
        if not bash.is_file():
            self.skipTest('Git Bash unavailable; PowerShell already checked')
        run = subprocess.run([str(bash),'--noprofile','--norc','-c',command],
            stdin=subprocess.DEVNULL,capture_output=True,text=True,cwd=self.folder,timeout=35)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertTrue(json.loads(run.stdout)['duplicate'])

    def test_exact_describe_gate_rejects_extra_arguments(self):
        self.setup_registration()
        payload = {'hook_event_name':'SessionStart','session_id':'new-session','cwd':str(self.folder)}
        result = self.cli('--harness','claude-code',payload=payload,cwd=self.folder)
        command = json.loads(result['hookSpecificOutput']['additionalContext'])['read_only_diagnostic_command']
        for suffix in ('; whoami','\nwhoami',' --config other.json',' -Manifest other.json',' && whoami'):
            result = self.cli('--harness','claude-code',payload={**payload,'hook_event_name':'PreToolUse',
                'tool_name':'Bash','tool_input':{'command':command+suffix}},cwd=self.folder)
            self.assertEqual(result['hookSpecificOutput']['permissionDecision'],'deny')


class MalformedLedgerTests(unittest.TestCase):
    setUp = test_registration.RegistrationTests.setUp
    tearDown = test_registration.RegistrationTests.tearDown
    bk = test_registration.RegistrationTests.bk

    def test_malformed_legacy_rows_refuse_without_writes(self):
        for name, fields in (('asset-registry.csv',ASSETS), ('interaction-log.csv',LOG)):
            path = self.root/name
            header = ','.join(fields)+'\n'
            cases = [header+','.join(['value']*(len(fields)+1))+'\n',
                     header+','.join(['value']*(len(fields)-1))+'\n',
                     header+','.join(['value']*(len(fields)-1))+',"unterminated\n',
                     header.rstrip()+',notes\n', '"unterminated', '']
            for body in cases:
                with self.subTest(name=name,body=body):
                    path.write_text(body,encoding='utf-8')
                    before = {str(p):p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
                    preview = execute(self.bk(),self.req)
                    self.assertTrue(preview['conflicts'])
                    self.assertFalse(preview['effects'])
                    self.assertEqual(preview['public_publication'],'not-attempted')
                    self.assertEqual(before,{str(p):p.read_bytes() for p in self.base.rglob('*') if p.is_file()})
            path.unlink()

    def test_describe_does_not_inspect_or_repair_ledgers(self):
        (self.root/'asset-registry.csv').write_text('malformed')
        before = {str(p):p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        output = io.StringIO()
        with patch.object(ingress,'Bookkeeper',side_effect=AssertionError('Describe opened state')),contextlib.redirect_stdout(output):
            self.assertEqual(ingress.main(['--describe']),0)
        self.assertIn('Source contract only',json.loads(output.getvalue())['installation_status'])
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.base.rglob('*') if p.is_file()})


class IntakeCompatibilityTests(unittest.TestCase):
    setUp = test_runtime.RuntimeTests.setUp
    tearDown = test_runtime.RuntimeTests.tearDown

    def test_linked_sources_are_rejected_on_supported_python(self):
        from aios_native.startup_intake import _revision, _entries
        from aios_native.bookkeeping import Refused
        target = self.base/'target'
        target.mkdir()
        directory = self.base/'listing'
        directory.mkdir()
        link = directory/'linked'
        if os.name == 'nt':
            run = subprocess.run(['cmd.exe','/c','mklink','/J',str(link),str(target)],
                                 capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        else:
            link.symlink_to(target,target_is_directory=True)
        try:
            with self.assertRaisesRegex(Refused,'intake-linked-source'):
                _revision(link)
            with self.assertRaisesRegex(Refused,'intake-linked-source'):
                _entries(directory,16)
        finally:
            if os.name == 'nt':
                link.rmdir()  # Remove only the junction; never recurse into its target.
            else:
                link.unlink()
        self.assertTrue(target.is_dir())


if __name__ == '__main__':
    unittest.main()
