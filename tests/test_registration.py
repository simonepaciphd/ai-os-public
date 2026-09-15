"""Disposable registration fixtures. No real project data or provider calls."""
import contextlib
import ctypes
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'runtime/src'))
from aios_native.bookkeeping import Bookkeeper, Refused, encoded, digest, csv_rows
from aios_native.registration import execute, ASSETS, LOG
from aios_native.request_contract import validate_request, examples
from aios_native.ingress import main


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.osroot = self.base/'os'
        self.root = self.base/'Existing Project'
        self.state = self.base/'state'
        self.config = self.base/'ownership.json'
        self.previous_cwd = Path.cwd()
        for p in [self.root,self.state,self.osroot/'coord/control',self.osroot/'coord/sessions',
                  self.osroot/'coord/mailbox',self.osroot/'coord/inbox',self.osroot/'memory/projects-ledger']:
            p.mkdir(parents=True)
        (self.osroot/'coord/SPEC.md').write_text('budgets: claude-code=4, codex-cli=4\n')
        (self.osroot/'coord/BOARD.md').write_text('No controls\n')
        (self.osroot/'memory/projects-ledger.md').write_text('# Ledger\n\n## Active projects\n\n| name | category | subtype | life_stage | priority | last_session | next_milestone |\n|---|---|---|---|---|---|---|\n')
        self.doc = dict(enabled=True,owner='v2',epoch='fixture',mode='rehearsal-sharded',rehearsal_root=str(self.base),
                        os_root=str(self.osroot),state_root=str(self.state),storage_format='project-session-v1',storage_generation='fixture',
                        custom={'preserve':['these','values']},projects={'ai-os-system':{'root':str(self.osroot),'provenance':False,'worktrees':[]}})
        self.config.write_bytes(encoded(self.doc))
        os.chdir(self.root)
        self.req = dict(operation='register-project',key='fixture-register',phase='preflight',root=str(self.root),
                        workspace=str(self.root),native_id='fixture-conversation',harness='codex-cli',name='Existing Project')

    def tearDown(self):
        os.chdir(self.previous_cwd)
        # Match the writer's Windows long-path opt-in for fixture cleanup only.
        assert self.base.parent == Path(tempfile.gettempdir()).resolve()
        assert self.base.name.startswith('tmp') and self.base != self.base.parent
        if os.name == 'nt':
            self.tmp.name = '\\\\?\\'+str(self.base)
        self.tmp.cleanup()

    def bk(self, **kw):
        return Bookkeeper(self.config, **kw)

    def preflight(self):
        validate_request(self.req)
        return execute(self.bk(), self.req)

    def apply_request(self):
        p = self.preflight()
        self.assertFalse(p['conflicts'], p)
        return {**self.req,'phase':'apply','preflight':p['preflight']}

    def register(self):
        return execute(self.bk(), self.apply_request())

    def test_missing_registration_and_actual_project_admission(self):
        p = self.preflight()
        self.assertEqual(p['admission']['status'],'not-yet-admitted')
        self.assertEqual(list(self.root.iterdir()), [])
        result = self.register()
        self.assertTrue(result['admission']['target_project_admitted'])
        self.assertEqual(result['public_publication'],'verified')
        cfg=json.loads(self.config.read_bytes())
        self.assertEqual(cfg['custom'],self.doc['custom'])
        self.assertEqual(cfg['projects']['ai-os-system'],self.doc['projects']['ai-os-system'])
        self.assertEqual(set(p.name for p in self.root.iterdir()),{'asset-registry.csv','interaction-log.csv'})

    def test_repeat_success_has_no_duplicate_changes(self):
        req = self.apply_request()
        execute(self.bk(),req)
        paths = [self.config,self.root/'asset-registry.csv',self.root/'interaction-log.csv',self.osroot/'memory/projects-ledger.md']
        before = {p:(p.read_bytes(),p.stat().st_mtime_ns) for p in paths}
        self.assertTrue(execute(self.bk(),req)['duplicate'])
        self.req['key']='second-registration'
        self.assertEqual(self.preflight()['proposed_changes'],[])
        self.register()
        self.assertEqual(before,{p:(p.read_bytes(),p.stat().st_mtime_ns) for p in paths})

    def test_os_root_keeps_real_binding(self):
        os.chdir(self.osroot)
        self.req['workspace']=str(self.osroot)
        r=self.register()
        self.assertEqual(r['admission']['project'],'ai-os-system')
        self.assertEqual(r['admission']['workspace'],str(self.osroot))
        self.assertFalse(r['admission']['target_project_admitted'])

    def test_fabricated_cwd_refused(self):
        self.req['workspace']=str(self.osroot)
        self.assertIn('registration-cwd-mismatch',self.preflight()['conflicts'])

    def test_conflicting_slug(self):
        self.doc['projects']['existing-project']={'root':str(self.base/'Other'),'provenance':True}
        self.config.write_bytes(encoded(self.doc))
        self.assertIn('registration-slug-conflict',self.preflight()['conflicts'])

    def test_duplicate_path(self):
        self.doc['projects']['first']={'root':str(self.root),'provenance':True}
        self.doc['projects']['second']={'root':str(self.root),'provenance':True}
        self.config.write_bytes(encoded(self.doc))
        self.assertIn('registration-path-conflict',self.preflight()['conflicts'])

    def test_existing_slug_inferred_from_path(self):
        self.doc['projects']['ratified-slug']={'root':str(self.root),'provenance':True}
        self.config.write_bytes(encoded(self.doc))
        self.assertEqual(self.preflight()['project'],'ratified-slug')

    def test_incomplete_bookkeeping_is_not_overwritten(self):
        p=self.root/'asset-registry.csv'
        p.write_text('asset_path,creator\nunfinished,agent\n')
        before=p.read_bytes()
        self.assertIn('unsupported-ledger-schema',self.preflight()['conflicts'])
        self.assertEqual(p.read_bytes(),before)
        self.assertNotIn('existing-project',json.loads(self.config.read_bytes())['projects'])

    def test_conflicting_ledger_path(self):
        p=self.osroot/'memory/projects-ledger/existing-project.md'
        p.write_text('---\nslug: existing-project\npath: '+str(self.base/'Other')+'\n---\nHistory\n')
        self.assertIn('registration-ledger-path-conflict',self.preflight()['conflicts'])

    def test_missing_folder_stanza_correction_preserves_history(self):
        p=self.osroot/'memory/projects-ledger/existing-project.md'
        p.write_text('---\nslug: existing-project\npath: PENDING\n---\nHistory is preserved\n')
        self.register()
        self.assertIn('History is preserved',p.read_text())
        self.assertIn('Registration correction',p.read_text())

    def test_concurrent_configuration_change(self):
        req=self.apply_request()
        self.doc['unrelated']='concurrent'
        self.config.write_bytes(encoded(self.doc))
        with self.assertRaisesRegex(Refused,'registration-stale-preflight'):
            execute(self.bk(),req)
        self.assertEqual(list(self.root.iterdir()),[])

    def test_concurrent_ledger_change(self):
        req=self.apply_request()
        p=self.osroot/'memory/projects-ledger.md'
        p.write_text(p.read_text()+'\nAnother editor\n')
        with self.assertRaisesRegex(Refused,'registration-stale-preflight'):
            execute(self.bk(),req)

    def test_interruption_recovered_at_each_write(self):
        req=self.apply_request()
        for n in range(5):
            def crash(label):
                if label == 'registration-after-write:'+str(n):
                    raise RuntimeError('simulated crash')
            try:
                execute(self.bk(fault=crash),req)
            except RuntimeError:
                pass
        r=execute(self.bk(),req)
        self.assertEqual(r['public_publication'],'verified')
        text=(self.osroot/'memory/projects-ledger.md').read_text()
        self.assertEqual(text.count('](projects-ledger/existing-project.md)'),1)

    def test_interrupted_conflict_preserved(self):
        req=self.apply_request()
        def crash(label):
            if label == 'registration-after-write:0':
                raise RuntimeError('simulated crash')
        with self.assertRaises(RuntimeError):
            execute(self.bk(fault=crash),req)
        p=self.osroot/'memory/projects-ledger/existing-project.md'
        p.write_text(p.read_text()+'\nConcurrent work\n')
        with self.assertRaisesRegex(Refused,'registration-concurrent-change'):
            execute(self.bk(),req)
        self.assertIn('Concurrent work',p.read_text())

    def delayed(self):
        p=self.root/'draft.md'
        p.write_bytes(b'Final stable fixture\n')
        self.req['delayed_artifacts']=[{'path':'draft.md','sha256':digest(p.read_bytes()),'text':True}]
        self.req['source']={'task':'original-task','date':'2026-09-14','harness':'codex-cli','model':'fixture-model'}
        return p

    def test_delayed_source_attribution_and_stable_snapshot(self):
        p=self.delayed()
        self.register()
        fields,rows=csv_rows(self.root/'asset-registry.csv',set(ASSETS))
        self.assertEqual(rows[0]['created'],'2026-09-14')
        self.assertIn('original-task',rows[0]['notes'])
        self.assertEqual(rows[0]['model_metadata'],'fixture-model / codex-cli')
        self.assertEqual((self.root/'.cowork/snapshots'/ (digest(p.read_bytes())+'.snap')).read_bytes(),p.read_bytes())
        self.req['key']='second-delayed'
        self.register()
        self.assertEqual(len(csv_rows(self.root/'interaction-log.csv',set(LOG))[1]),1)

    def test_changing_artifact_between_reads(self):
        p=self.delayed()
        def change(label):
            if label == 'registration-after-artifact-read':
                p.write_text('still arriving')
        r=execute(self.bk(fault=change),self.req)
        self.assertIn('artifact-changing',r['conflicts'])
        self.assertFalse((self.root/'asset-registry.csv').exists())

    def test_changed_artifact_after_preflight(self):
        p=self.delayed()
        req=self.apply_request()
        p.write_text('later revision')
        with self.assertRaisesRegex(Refused,'artifact-hash-mismatch'):
            execute(self.bk(),req)

    def test_shutdown_refuses_new_effects(self):
        (self.osroot/'coord/control/SHUTDOWN-REQUESTED.md').write_text('shutdown')
        self.assertIn('cleanup-only',self.preflight()['conflicts'])

    def test_live_claim_blocks_registration(self):
        # Native writer claim admission, no hand-written native session fields.
        other=self.bk().execute(dict(operation='start',key='other',project='ai-os-system',native_id='other',
                                   harness='codex-cli',worktree=str(self.osroot),claims=[str(self.root)]))
        self.assertTrue(any(c.startswith('claim-overlap:') for c in self.preflight()['conflicts']))

    def test_intake_not_admitted_is_precise(self):
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            code=main(['--config',str(self.config),'--intake','--harness','codex-cli',
                       '--native-id','absent','--workspace',str(self.root)])
        r=json.loads(out.getvalue())
        self.assertEqual(code,2)
        self.assertEqual(r['classification'],'native-not-yet-admitted')
        self.assertNotIn('FileNotFoundError',out.getvalue())

    def test_current_examples_validate(self):
        for req in examples().values():
            validate_request(req)

    def test_completed_retry_detects_later_publication_drift(self):
        req=self.apply_request()
        execute(self.bk(),req)
        p=self.osroot/'memory/projects-ledger/existing-project.md'
        p.write_text(p.read_text()+'\nNewer authorized edit\n')
        with self.assertRaisesRegex(Refused,'registration-publication-drift'):
            execute(self.bk(),req)
        self.assertIn('Newer authorized edit',p.read_text())
        self.req['key']='fresh-preflight-after-edit'
        self.assertEqual(self.preflight()['proposed_changes'],[])
        self.register()

    def test_recovery_detects_new_conflicting_stanza(self):
        req=self.apply_request()
        def crash(label):
            if label == 'registration-after-journal':
                raise RuntimeError('simulated crash')
        with self.assertRaises(RuntimeError):
            execute(self.bk(fault=crash),req)
        p=self.osroot/'memory/projects-ledger/competitor.md'
        p.write_text('---\nslug: competitor\npath: '+str(self.root)+'\n---\n')
        with self.assertRaisesRegex(Refused,'registration-concurrent-change'):
            execute(self.bk(),req)

    @unittest.skipUnless(os.name == 'nt','Windows DACL preservation')
    def test_config_permissions_preserved(self):
        def acl():
            length=ctypes.c_ulong()
            api=ctypes.windll.advapi32.GetFileSecurityW
            api(str(self.config),7,None,0,ctypes.byref(length))
            buffer=ctypes.create_string_buffer(length.value)
            if not api(str(self.config),7,buffer,length.value,ctypes.byref(length)):
                raise ctypes.WinError()
            result=bytearray(buffer.raw)
            # Windows normalizes auto-inheritance provenance on replacement.
            # Compare owner/group, protection, every principal/access mask and
            # inheritance behavior; ignore only historical "inherited" labels.
            result[3] &= ~4
            offset=int.from_bytes(result[16:20],'little')
            count=int.from_bytes(result[offset+4:offset+6],'little')
            position=offset+8
            for _ in range(count):
                result[position+1] &= ~16  # INHERITED_ACE, not OI/CI/IO/NP.
                position+=int.from_bytes(result[position+2:position+4],'little')
            return bytes(result)
        before=acl()
        self.register()
        self.assertEqual(acl(),before)

    def test_semantic_entrypoint_end_to_end(self):
        request=self.base/'request.json'
        request.write_bytes(encoded(self.req))
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            code=main(['--config',str(self.config),'--request',str(request)])
        self.assertEqual(code,0)
        self.req.update(phase='apply',preflight=json.loads(out.getvalue())['preflight'])
        request.write_bytes(encoded(self.req))
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            code=main(['--config',str(self.config),'--request',str(request)])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(out.getvalue())['configuration'],'registered')

    def test_existing_native_lifecycle_still_works(self):
        r=self.register()
        bk=self.bk()
        activation=r['admission']['activation']
        bk.execute(dict(operation='checkpoint',key='check',activation=activation,summary='Fixture lifecycle'))
        bk.execute(dict(operation='resume',key='resume',activation=activation))
        closed=bk.execute(dict(operation='close',key='close',activation=activation,summary='Fixture done',input_summary='Fixture',relaunch='no'))
        self.assertEqual(closed['status'],'closed')
        with self.assertRaisesRegex(Refused,'explicit-activation-required'):
            execute(self.bk(),{**self.req,'phase':'apply','preflight':'0'*64})

    def test_pending_registration_blocks_a_different_key(self):
        req=self.apply_request()
        def crash(label):
            if label == 'registration-after-journal':
                raise RuntimeError('simulated crash')
        with self.assertRaises(RuntimeError):
            execute(self.bk(fault=crash),req)
        self.req['key']='different-key'
        self.assertTrue(self.preflight()['conflicts'][0].startswith('registration-pending-request:'))
        with self.assertRaisesRegex(Refused,'registration-pending-request'):
            execute(self.bk(),{**req,'key':'different-key'})
        self.assertEqual(execute(self.bk(),req)['public_publication'],'verified')

    def test_delayed_artifact_order_does_not_duplicate_log(self):
        self.delayed()
        other=self.root/'other.md'
        other.write_text('Second stable file')
        self.req['delayed_artifacts'].append({'path':'other.md','sha256':digest(other.read_bytes())})
        self.register()
        self.req['key']='reordered'
        self.req['delayed_artifacts'].reverse()
        self.register()
        self.assertEqual(len(csv_rows(self.root/'interaction-log.csv',set(LOG))[1]),1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
