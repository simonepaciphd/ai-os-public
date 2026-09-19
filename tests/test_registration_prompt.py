"""Exercise unregistered Claude conversation recovery in disposable local roots."""
import contextlib
import io
import json
import os
from pathlib import Path
import hashlib
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_registration as registration_fixture
from aios_native import ingress
from aios_native.bookkeeping import Refused, encoded
from aios_native.registration import execute


class RegistrationPromptTests(unittest.TestCase):
    setUp = registration_fixture.RegistrationTests.setUp
    tearDown = registration_fixture.RegistrationTests.tearDown
    bk = registration_fixture.RegistrationTests.bk
    preflight = registration_fixture.RegistrationTests.preflight
    apply_request = registration_fixture.RegistrationTests.apply_request
    register = registration_fixture.RegistrationTests.register

    def payload(self, event='UserPromptSubmit', **kwargs):
        return dict(hook_event_name=event, session_id='new-conversation', cwd=str(Path.cwd()),
                    prompt='PRIVATE_PROMPT_SENTINEL', transcript_path='PRIVATE_TRANSCRIPT_SENTINEL', **kwargs)

    def hook(self, event='UserPromptSubmit', harness='claude-code', **kwargs):
        out, err = io.StringIO(), io.StringIO()
        with patch('sys.stdin', io.StringIO(json.dumps(self.payload(event, **kwargs)))), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ingress.main(['--config',str(self.config),'--harness',harness])
        return code, json.loads(out.getvalue()), err.getvalue()

    def invoke_registration(self, project='new-project', kind='new', fault=None):
        out = io.StringIO()
        args = ['--config',str(self.config),'--register-cwd','--harness','claude-code',
                '--native-id','new-conversation','--workspace',str(Path.cwd()),
                '--project',project,'--registration-kind',kind]
        with contextlib.redirect_stdout(out):
            if fault:
                with patch.object(ingress, 'Bookkeeper', side_effect=lambda p: self.bk(fault=fault)):
                    code = ingress.main(args)
            else:
                code = ingress.main(args)
        return code, json.loads(out.getvalue())

    def existing_project(self):
        self.register()
        self.website = self.base/'website'
        self.website.mkdir()
        os.chdir(self.website)

    def test_prompt_reaches_agent_without_admission_or_private_body(self):
        for event in ('SessionStart','UserPromptSubmit'):
            code, result, err = self.hook(event)
            self.assertEqual(code, 0)
            self.assertNotIn('continue',result)
            context = json.loads(result['hookSpecificOutput']['additionalContext'])
            self.assertEqual(context['aios']['status'],'registration-required')
            self.assertFalse(context['aios']['admitted'])
            self.assertIn('ask the user',context['instruction'])
            self.assertIn('already explicitly names',context['instruction'])
            self.assertNotIn('PRIVATE_',json.dumps(result)+err)
            self.assertEqual(list((self.osroot/'coord/sessions').glob('*.md')),[])
            self.assertEqual(list(self.root.iterdir()),[])

    def test_question_and_lifecycle_are_nonblocking(self):
        for event in ('PreToolUse','PostToolUse','PostToolUseFailure','Stop','SessionEnd'):
            code, result, _ = self.hook(event,tool_name='AskUserQuestion',tool_input={'questions':'PRIVATE_QUESTION'},tool_response='PRIVATE_ANSWER')
            self.assertEqual((code,result),(0,{}))

    def test_ordinary_tools_denied_without_stopping_conversation(self):
        for tool in ('Bash','Read','Write','Agent','mcp__anything'):
            code, result, _ = self.hook('PreToolUse',tool_name=tool,tool_input={'command':'git status'})
            self.assertEqual(code,0)
            self.assertNotIn('continue',result)
            self.assertEqual(result['hookSpecificOutput']['permissionDecision'],'deny')

    def test_only_exact_registration_command_is_available(self):
        command = ingress.registration_command(self.bk(),self.payload(),'sample','existing')
        for tool in ('Bash','PowerShell'):
            self.assertEqual(self.hook('PreToolUse',tool_name=tool,tool_input={'command':command})[:2],(0,{}))
        attacks = [command+'; git status',command+'\nwhoami',command+' && whoami',command+' -Manifest evil.json',
                   command.replace(' --register-cwd',' --describe'),command.replace('sample','$(whoami)'),
                   command.replace('new-conversation','different-conversation'),command.replace(' -I -B ', ' -B ')]
        for command in attacks:
            with self.subTest(command=command):
                result = self.hook('PreToolUse',tool_name='Bash',tool_input={'command':command})[1]
                self.assertEqual(result['hookSpecificOutput']['permissionDecision'],'deny')
        command = ingress.registration_command(self.bk(),self.payload(),'sample','existing')
        result=self.hook('PreToolUse',tool_name='Bash',tool_input={'command':command,'run_in_background':True})[1]
        self.assertEqual(result['hookSpecificOutput']['permissionDecision'],'deny')

    def test_register_new_and_continue_same_conversation(self):
        code,result=self.invoke_registration()
        self.assertEqual(code,0)
        self.assertEqual(result['public_publication'],'verified')
        self.assertTrue(result['admission']['target_project_admitted'])
        code, hook, _ = self.hook()
        self.assertEqual(code,0)
        context=json.loads(hook['hookSpecificOutput']['additionalContext'])
        self.assertEqual(context['aios']['activation'],result['admission']['activation'])
        self.assertEqual(self.hook('PreToolUse',tool_name='Bash',tool_input={'command':'git status'})[:2],(0,{}))
        self.assertTrue(self.invoke_registration()[1]['duplicate'])

    def test_attach_existing_preserves_root_ledger_and_repository(self):
        self.existing_project()
        stanza=self.osroot/'memory/projects-ledger/existing-project.md'
        index=self.osroot/'memory/projects-ledger.md'
        before={p:p.read_bytes() for p in (stanza,index)}
        code,result=self.invoke_registration('existing-project','existing')
        self.assertEqual(code,0,result)
        self.assertEqual(result['admission']['project'],'existing-project')
        self.assertEqual(result['admission']['workspace'],str(self.website))
        cfg=json.loads(self.config.read_bytes())['projects']['existing-project']
        self.assertEqual(cfg['root'],str(self.root))
        self.assertEqual(cfg['worktrees'],[str(self.website)])
        self.assertEqual(before,{p:p.read_bytes() for p in before})
        self.assertEqual(list(self.website.iterdir()),[])
        self.assertEqual(self.hook()[0],0)
        self.assertTrue(self.invoke_registration('existing-project','existing')[1]['duplicate'])

    def test_typo_does_not_create_project(self):
        code,result=self.invoke_registration('typo','existing')
        self.assertEqual(code,2)
        self.assertEqual(result['classification'],'registration-existing-project-required')
        self.assertEqual(json.loads(self.config.read_bytes()),self.doc)

    def test_new_cannot_replace_existing_project(self):
        self.existing_project()
        before=self.config.read_bytes()
        code,result=self.invoke_registration('existing-project','new')
        self.assertEqual(code,2)
        self.assertEqual(result['classification'],'registration-slug-conflict')
        self.assertEqual(before,self.config.read_bytes())

    def test_shutdown_and_disabled_owner_never_offer_registration(self):
        flag=self.osroot/'coord/control/SHUTDOWN-REQUESTED.md'
        flag.write_text('stop')
        self.assertTrue(self.hook()[1]['continue'] is False)
        self.assertTrue(self.invoke_registration()[1]['conflicts'])
        flag.unlink()
        self.doc['enabled']=False
        self.config.write_bytes(encoded(self.doc))
        self.assertTrue(self.hook()[1]['continue'] is False)

    def test_existing_binding_cannot_be_repurposed(self):
        self.invoke_registration()
        other=self.base/'other'
        other.mkdir()
        os.chdir(other)
        result=self.hook()[1]
        self.assertTrue(result['continue'] is False)
        self.assertNotIn('registration-required',json.dumps(result))

    def test_closed_binding_cannot_enter_registration_flow(self):
        _,r=self.invoke_registration()
        self.bk().execute(dict(operation='close',key='close',activation=r['admission']['activation']))
        cfg=json.loads(self.config.read_bytes())
        del cfg['projects']['new-project']
        self.config.write_bytes(encoded(cfg))
        result=self.hook()[1]
        self.assertTrue(result['continue'] is False)
        self.assertIn('already closed',result['stopReason'])

    def test_other_harness_retains_stop_and_actionable_guidance(self):
        code,result,_=self.hook(harness='codex-cli')
        self.assertEqual(code,2)
        self.assertFalse(result['continue'])
        self.assertIn('Ask the user which project',result['stopReason'])
        self.assertNotIn('then an explicit resume',result['stopReason'])

    def test_workspace_claim_blocks_attachment(self):
        self.existing_project()
        self.bk().execute(dict(operation='start',key='holder',project='ai-os-system',native_id='holder',
                              harness='codex-cli',worktree=str(self.osroot),claims=[str(self.website)]))
        before=self.config.read_bytes()
        code,result=self.invoke_registration('existing-project','existing')
        self.assertEqual(code,2)
        self.assertTrue(any(x.startswith('claim-overlap:') for x in result['conflicts']))
        self.assertEqual(before,self.config.read_bytes())

    def test_workspace_cannot_overlap_another_project(self):
        self.existing_project()
        cfg=json.loads(self.config.read_bytes())
        cfg['projects']['another']={'root':str(self.website),'provenance':True,'worktrees':[]}
        self.config.write_bytes(encoded(cfg))
        code,result=self.invoke_registration('existing-project','existing')
        self.assertEqual(code,2)
        self.assertIn('registration-overlapping-project-root',result['conflicts'])

    def test_alias_read_access_failure_is_not_missing_admission(self):
        with patch('aios_native.sharded.shared_read',side_effect=PermissionError(13,'denied')):
            result=self.hook()[1]
        self.assertTrue(result['continue'] is False)
        self.assertNotIn('registration-required',json.dumps(result))

    def test_interrupted_attachment_recovers_same_request(self):
        self.existing_project()
        def crash(label):
            if label=='registration-after-write:0':
                raise RuntimeError('simulated crash')
        with self.assertRaisesRegex(RuntimeError,'simulated crash'):
            self.invoke_registration('existing-project','existing',fault=crash)
        code,result=self.invoke_registration('existing-project','existing')
        self.assertEqual(code,0,result)
        self.assertTrue(result['recovered'])
        self.assertEqual(result['public_publication'],'verified')

    def test_readonly_subtree_cannot_be_attached(self):
        self.existing_project()
        target=self.website/'inputs'
        target.mkdir()
        os.chdir(target)
        code,result=self.invoke_registration('existing-project','existing')
        self.assertEqual(code,2)
        self.assertIn('registration-root-forbidden',result['conflicts'])

    def test_recovery_only_does_not_offer_registration(self):
        self.doc['recovery_only']=True
        self.config.write_bytes(encoded(self.doc))
        result=self.hook()[1]
        self.assertFalse(result['continue'])
        self.assertNotIn('registration-required',json.dumps(result))

    def test_placeholder_words_in_path_stay_literal(self):
        target=self.base/'PROJECT_SLUG-REGISTRATION_KIND'
        target.mkdir()
        os.chdir(target)
        command=ingress.registration_command(self.bk(),self.payload(),'sample','existing')
        self.assertEqual(self.hook('PreToolUse',tool_name='Bash',tool_input={'command':command})[:2],(0,{}))
        changed=command.replace('PROJECT_SLUG-REGISTRATION_KIND','other-existing')
        result=self.hook('PreToolUse',tool_name='Bash',tool_input={'command':changed})[1]
        self.assertEqual(result['hookSpecificOutput']['permissionDecision'],'deny')


if __name__=='__main__':
    unittest.main()
