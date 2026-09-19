"""Existing-folder registration, inside the native writer; no folder retrofit.

Private redo plans retain exact bytes and preimages. All registration writers use
one registration lock and the existing shared-resource locks. External editors
remain advisory participants: preimage checks detect observed changes, not ABA.
"""
from __future__ import annotations

import copy
import csv
import ctypes
import io
import json
import os
from pathlib import Path
import re
import stat
import time
import uuid
from datetime import datetime

from .bookkeeping import (Bookkeeper, Refused, digest, encoded, hash_at, read,
                          csv_bytes, csv_rows, workspace_matches, beneath)

ASSETS = 'asset_path asset_type creator model_metadata created last_modified verification notes ai_output_hash'.split()
LOG = 'date session_id harness model researcher_input_summary agent_output_summary assets_affected notes initiator task_difficulty decisions'.split()
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')


def scalar(value):
    # Values are also rendered in Markdown/YAML. Refuse markup delimiters rather
    # than letting a title accidentally produce an extra row or field.
    if not isinstance(value, str) or not value.strip() or any(c in value for c in '\r\n\0|[]'):
        raise Refused('registration-invalid-metadata')
    return value


def identity(bk, req):
    """Verify the actual invoking cwd; a target folder is never an identity alias."""
    cwd = Path(req['workspace']).resolve(strict=True)
    if cwd != Path.cwd().resolve():
        raise Refused('registration-cwd-mismatch')
    alias = bk.root/'aliases'/(digest((req['harness']+':'+req['native_id']).encode())+'.json')
    from .sharded import shared_read
    try:
        binding = shared_read(alias)
    except FileNotFoundError:
        return None
    state = bk._session(json.loads(binding)['activation'])
    if state['native_id'] != req['native_id'] or state['harness'] != req['harness']:
        raise Refused('native-identity-mismatch')
    if Path(state['workspace']).resolve() != cwd:
        raise Refused('registration-cwd-mismatch')
    if state['epoch'] != bk.config['epoch']:
        raise Refused('activation-epoch-mismatch')
    if state['status'] != 'active':
        raise Refused('explicit-activation-required')
    age = (bk.clock()-datetime.fromisoformat(state['heartbeat'])).total_seconds()
    if not -300 <= age <= 3600:
        raise Refused('fresh-resume-required')
    return state


def stable(path):
    def signature():
        s = path.stat()
        if not stat.S_ISREG(s.st_mode):
            raise Refused('registration-not-regular-file')
        return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    before = signature()
    body = path.read_bytes()
    if signature() != before:
        raise Refused('artifact-changing')
    return body


def replace_preserving_permissions(path, body, expected, check):
    """Preserve destination DACL on Windows and mode on POSIX; no ACL edits."""
    check()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name+'.registration-'+uuid.uuid4().hex+'.tmp')
    try:
        with tmp.open('xb') as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        check()
        if hash_at(path) != expected:
            raise Refused('registration-concurrent-change')
        if expected is None:
            if os.name == 'nt':
                os.rename(tmp, path)  # Windows rename refuses an existing target.
            else:
                os.link(tmp, path)  # Exclusive publication, never overwrite.
                tmp.unlink()
        elif os.name == 'nt':
            if not ctypes.windll.kernel32.ReplaceFileW(str(path), str(tmp), None, 0, None, None):
                raise ctypes.WinError()
        else:
            os.chmod(tmp, stat.S_IMODE(path.stat().st_mode))
            os.replace(tmp, path)
        if hash_at(path) != digest(body):
            raise Refused('registration-postimage-mismatch')
    finally:
        if tmp.exists():
            tmp.unlink()


def frontmatter(body):
    text = body.decode('utf-8-sig')
    if not text.startswith('---\n') and not text.startswith('---\r\n'):
        raise Refused('registration-incomplete-stanza')
    parts = text.split('---', 2)
    if len(parts) != 3:
        raise Refused('registration-incomplete-stanza')
    result = {}
    for row in parts[1].splitlines():
        if not row.strip():
            continue
        if ':' not in row:
            raise Refused('registration-incomplete-stanza')
        key, value = row.split(':', 1)
        if key in result:
            raise Refused('registration-duplicate-stanza-field')
        value = value.strip()
        if value.startswith('"'):
            value = json.loads(value)
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1].replace("''", "'")
        result[key] = value
    return result


def plan(bk, req):
    bk.ownership()
    if not getattr(bk, 'sharded', False):
        raise Refused('registration-requires-project-session-v1')
    if bk.control() != 'clear' or bk.config.get('recovery_only'):
        raise Refused('cleanup-only')
    caller = identity(bk, req)
    root = Path(req['root']).resolve(strict=True)
    if not root.is_dir():
        raise Refused('registration-root-not-directory')
    for journal in (bk.root/'registrations').glob('*.json'):
        if journal.stem == digest(req['key'].encode()):
            continue
        pending = json.loads(journal.read_bytes())
        if not pending['complete'] and Path(pending['payload']['root']) == root:
            raise Refused('registration-pending-request:'+journal.stem)
    # A configured project may be a child of the coordination-only OS root.
    # Private state and source-material trees never become project roots.
    if beneath(root, bk.root) or root == bk.os_root or any(x.lower() in {'inputs','background','.git','.cowork'} for x in root.parts):
        raise Refused('registration-root-forbidden')
    if bk.config.get('mode') == 'rehearsal-sharded' and not beneath(root, Path(bk.config['rehearsal_root'])):
        raise Refused('rehearsal-path-outside-root')
    observed = {str(bk.config_path): hash_at(bk.config_path)}
    writes = {}

    def observe(path):
        body = read(path)
        sha = digest(body) if body is not None else None
        if str(path) in observed and observed[str(path)] != sha:
            raise Refused('registration-concurrent-change')
        observed[str(path)] = sha
        return body

    def propose(path, body):
        before = observe(path)
        if before != body:
            writes[str(path)] = {'path': str(path), 'before': observed[str(path)],
                                 'after': digest(body), 'body': body.hex()}

    directory = bk.os_root/'memory/projects-ledger'
    if not directory.is_dir():
        raise Refused('registration-ledger-directory-missing')
    stanzas = {}
    for p in sorted(directory.glob('*.md')):
        if p.name.startswith('_'):
            continue
        body = observe(p)
        data = frontmatter(body)
        stanzas[p.stem] = data
    inventory = sorted(stanzas)
    matches = {slug for slug, value in bk.config['projects'].items()
               if any(Path(p).resolve() == root for p in [value['root']]+value.get('worktrees', []))}
    matches |= {slug for slug, value in stanzas.items()
                if value.get('path') and Path(value['path']).is_absolute() and Path(value['path']).resolve() == root}
    if len(matches) > 1:
        raise Refused('registration-path-conflict')
    slug = req.get('project') or next(iter(matches), re.sub(r'[^a-z0-9]+', '-', root.name.lower()).strip('-'))
    if not SLUG.fullmatch(slug):
        raise Refused('registration-slug-required')
    if matches and matches != {slug}:
        raise Refused('registration-path-conflict')
    existing = bk.config['projects'].get(slug)
    if existing and Path(existing['root']).resolve() != root:
        raise Refused('registration-slug-conflict')
    if existing and not existing.get('provenance', True):
        raise Refused('registration-provenance-conflict')
    for other, value in bk.config['projects'].items():
        if other == slug or not value.get('provenance', True):
            continue
        for p in [value['root']]+value.get('worktrees', []):
            if beneath(root, Path(p)) or beneath(Path(p), root):
                raise Refused('registration-overlapping-project-root')
    data = stanzas.get(slug, {})
    if data.get('slug', slug) != slug:
        raise Refused('registration-stanza-slug-conflict')
    old_path = data.get('path', '')
    if old_path and old_path not in {'PENDING', '<TO FILL>', 'none', 'not created'}:
        if not Path(old_path).is_absolute() or Path(old_path).resolve() != root:
            raise Refused('registration-ledger-path-conflict')
    metadata = {k: scalar(req.get(k) or data.get(k) or (root.name if k == 'name' else 'PENDING'))
                for k in ('name','category','subtype')}
    for k in metadata:
        if k in req and data.get(k) and data[k] not in {'PENDING','<TO FILL>'} and req[k] != data[k]:
            raise Refused('registration-metadata-conflict')
    date = bk.clock().date().isoformat()
    stanza_path = directory/(slug+'.md')
    stanza = observe(stanza_path)
    if stanza is None:
        fm = {**metadata, 'slug': slug, 'path': str(root), 'audience_tier': 'personal',
              'created': 'PENDING', 'last_ledger_update': date}
        text = '---\n'+'\n'.join(k+': '+json.dumps(v, ensure_ascii=False) for k,v in fm.items())+'\n---\n\n'
        text += '# '+metadata['name']+'\n\n## Identification\n- **path:** `'+str(root)+'`\n'
        text += '- **skill library wired:** PENDING\n- **overleaf linked:** PENDING\n\n## State\n'
        text += '\n'.join('- **'+k+':** PENDING' for k in ('life_stage','priority','current_phase','next_milestone','deadline','blocker','last_session_date','primary_persona'))
        text += '\n\n## Collaboration\n- **coauthors:** PENDING\n- **ra_assignments:** PENDING\n\n## Funding\n- **funded_by:** PENDING\n'
        text += '\n## Notes\nExisting folder registered without restructuring. Unknown operational metadata remains PENDING.\n'
        text += '\n## Update log\n- '+date+' — registered existing folder through native register-project.\n'
        propose(stanza_path, text.encode())
    elif not old_path or old_path in {'PENDING','<TO FILL>','none','not created'}:
        text = stanza.decode('utf-8-sig')
        head, fm, tail = text.split('---', 2)
        fm = re.sub(r'(?m)^path:.*$', lambda _: 'path: '+json.dumps(str(root)), fm) if 'path' in data else fm+'path: '+json.dumps(str(root))+'\n'
        text = head+'---'+fm+'---'+tail
        # Do not rewrite prose that may contain substantive project history.
        text += '\n## Registration correction\n- '+date+' — canonical existing folder: `'+str(root)+'`; supersedes earlier missing-folder descriptions.\n'
        propose(stanza_path, text.encode())
    index = bk.os_root/'memory/projects-ledger.md'
    index_body = observe(index)
    if index_body is None:
        raise Refused('registration-project-index-missing')
    text = index_body.decode('utf-8-sig')
    links = re.findall(r'\]\(projects-ledger/([a-z0-9-]+)\.md\)', text)
    if links.count(slug) > 1:
        raise Refused('registration-duplicate-index-row')
    if slug not in links:
        marker = '|---|---|---|---|---|---|---|'
        start = text.find('## Active projects')
        position = text.find(marker, start)
        if start < 0 or position < 0:
            raise Refused('registration-index-schema')
        position = text.find('\n', position)
        row = '\n| ['+metadata['name']+'](projects-ledger/'+slug+'.md) | '+metadata['category']+' | '+metadata['subtype']+' | unclear | <TO FILL> | PENDING | <TO FILL> |'
        propose(index, (text[:position]+row+text[position:]).encode())
    missing = []
    for name, fields in [('asset-registry.csv', ASSETS), ('interaction-log.csv', LOG)]:
        p = root/name
        body = observe(p)
        if body is None:
            missing.append(name)
            propose(p, csv_bytes(fields, []))
        else:
            csv_rows(p, set(fields))  # Malformed/incomplete files are never overwritten.
    artifacts = req.get('delayed_artifacts', [])
    artifact_checks = []
    if artifacts:
        # Metadata does not pretend the logger was the original author/session.
        source = req['source']
        datetime.strptime(source['date'], '%Y-%m-%d')
        for field in ('task','date','harness','model'):
            scalar(source[field])
        fieldnames, rows = (csv_rows(root/'asset-registry.csv', set(ASSETS)) if (root/'asset-registry.csv').exists() else (ASSETS, []))
        seen = set()
        for item in artifacts:
            relative = item['path'].replace('\\', '/')
            path = (root/relative).resolve(strict=True)
            if Path(relative).is_absolute() or not beneath(path, root) or '..' in Path(relative).parts or path == root:
                raise Refused('artifact-outside-project')
            if any(p.lower() in {'inputs','background','.git','.cowork'} for p in path.relative_to(root).parts) or path.name in {'asset-registry.csv','interaction-log.csv'}:
                raise Refused('artifact-readonly-or-bookkeeping')
            if str(path).casefold() in seen:
                raise Refused('duplicate-artifact')
            seen.add(str(path).casefold())
            body = stable(path)
            sha = digest(body)
            if sha != item['sha256']:
                raise Refused('artifact-hash-mismatch')
            artifact_checks.append({'path': str(path), 'sha256': sha})
            bk.fault('registration-after-artifact-read')
            if digest(stable(path)) != sha:
                raise Refused('artifact-changing')
            candidates = [r for r in rows if r['asset_path'].replace('\\','/').casefold() == relative.casefold()]
            if len(candidates) > 1:
                raise Refused('duplicate-registry-row')
            if candidates and candidates[0]['verification'] == 'human-verified':
                raise Refused('registration-human-verification-conflict')
            row = candidates[0] if candidates else {k:'' for k in fieldnames}
            row.update(asset_path=relative, asset_type=item.get('asset_type','other'), creator=item.get('creator','agent'),
                       model_metadata=source['model']+' / '+source['harness'], created=row.get('created') or source['date'],
                       last_modified=source['date'], verification=item.get('verification','not-verified'),
                       notes='Delayed logging; source task '+source['task']+'; source date '+source['date']+'; original admission unverified.',
                       ai_output_hash=sha if item.get('text',True) else '')
            if not candidates:
                rows.append(row)
            if item.get('text', True):
                snap = root/'.cowork/snapshots'/(sha+'.snap')
                if snap.exists() and hash_at(snap) != sha:
                    raise Refused('snapshot-integrity-failed')
                propose(snap, body)
        propose(root/'asset-registry.csv', csv_bytes(fieldnames, rows))
        log_fields, log_rows = (csv_rows(root/'interaction-log.csv', set(LOG)) if (root/'interaction-log.csv').exists() else (LOG, []))
        log_id = 'delayed-'+digest(encoded({'project':slug, 'source':source,
            'artifacts':sorted(artifact_checks, key=lambda a:a['path'])}))[:24]
        if sum(r['session_id'] == log_id for r in log_rows) > 1:
            raise Refused('interaction-row-collision')
        if not any(r['session_id'] == log_id for r in log_rows):
            row = {k:'' for k in log_fields}
            row.update(date=source['date'], session_id=log_id, harness=source['harness'], model=source['model'],
                       researcher_input_summary='Explicitly authorized delayed artifact logging',
                       agent_output_summary='Verified stable source bytes and published exact snapshots',
                       assets_affected='; '.join(a['path'] for a in artifacts),
                       notes='Source task '+source['task']+'; logged '+date+' by '+req['native_id']+'; original admission and close unverified.', initiator='human')
            log_rows.append(row)
            propose(root/'interaction-log.csv', csv_bytes(log_fields, log_rows))
    config = copy.deepcopy(bk.config)
    attachment = None
    if req.get('attach_workspace'):
        if not existing or not req.get('project'):
            raise Refused('registration-existing-project-required')
        attachment = Path(req['workspace']).resolve(strict=True)
        if (not attachment.is_dir() or attachment == bk.os_root or beneath(attachment, bk.root)
                or any(x.lower() in {'inputs','background','.git','.cowork'} for x in attachment.parts)):
            raise Refused('registration-root-forbidden')
        if bk.config.get('mode') == 'rehearsal-sharded' and not beneath(attachment, Path(bk.config['rehearsal_root'])):
            raise Refused('rehearsal-path-outside-root')
        if caller and caller['project'] != slug:
            raise Refused('native-project-changed')
        for other, value in bk.config['projects'].items():
            for p in [value['root']]+value.get('worktrees', []):
                base = Path(p).resolve()
                if not value.get('provenance', True):
                    if attachment == base or beneath(base, attachment):
                        raise Refused('registration-overlapping-project-root')
                elif other != slug and (beneath(attachment, base) or beneath(base, attachment)):
                    raise Refused('registration-overlapping-project-root')
                elif other == slug and attachment != base and beneath(base, attachment):
                    raise Refused('registration-overlapping-project-root')
        if not any(workspace_matches(existing, attachment, Path(p))
                   for p in [existing['root']]+existing.get('worktrees', [])):
            config['projects'][slug].setdefault('worktrees', []).append(str(attachment))
            propose(bk.config_path, encoded(config))
    if not existing:
        config['projects'][slug] = {'root':str(root), 'provenance':True, 'worktrees':[]}
        propose(bk.config_path, encoded(config))  # Configuration last: provenance is ready first.
    paths = list(writes)
    bk.check_claims(paths + [a['path'] for a in artifact_checks] + ([str(attachment)] if attachment else []), caller['id'] if caller else '')
    bk.ownership()
    payload = {'project':slug, 'root':str(root), 'writes':list(writes.values()), 'observed':observed,
               'stanza_inventory':inventory, 'artifacts':artifact_checks,
               **({'attachment':str(attachment)} if attachment else {})}
    token = digest(encoded(payload))
    return payload, {'project':slug, 'canonical_root':str(root), 'configuration':'present' if existing else 'missing',
        'ledger':'present' if stanza is not None and slug in links else 'incomplete',
        'missing_bookkeeping':missing, 'missing_project_docs':[n for n in ('README.md','implementation-roadmap.md') if not (root/n).is_file()],
        'pending_metadata':[k for k,v in metadata.items() if v == 'PENDING'],
        'conflicts':[], 'proposed_changes':[str(Path(p)) for p in writes], 'preflight':token,
        'admission':{'status':'active' if caller else 'not-yet-admitted', 'activation':caller['id'] if caller else None,
                     'project':caller['project'] if caller else None, 'workspace':str(Path(req['workspace']).resolve())},
        'public_publication':'not-attempted', 'host_receipt_delivery':'unverified', 'effects':False}


def verify_observations(bk, payload):
    inventory = sorted(p.stem for p in (bk.os_root/'memory/projects-ledger').glob('*.md') if not p.name.startswith('_'))
    if inventory != payload['stanza_inventory']:
        raise Refused('registration-concurrent-change')
    for p, sha in payload['observed'].items():
        if hash_at(Path(p)) != sha:
            raise Refused('registration-concurrent-change')


def execute(bk, req):
    if req['phase'] == 'preflight':
        try:
            return plan(bk, req)[1]
        except Refused as exc:
            return {'effects':False, 'conflicts':[str(exc)], 'public_publication':'not-attempted', 'host_receipt_delivery':'unverified'}
    if not req.get('preflight'):
        raise Refused('registration-preflight-required')
    bk.ownership()
    if not getattr(bk, 'sharded', False):
        raise Refused('registration-requires-project-session-v1')
    caller = identity(bk, req)
    deadline = time.monotonic()+20
    journal = bk.root/'registrations'/(digest(req['key'].encode())+'.json')
    with bk._lock('registration', deadline):
        for other in (bk.root/'registrations').glob('*.json'):
            if other == journal:
                continue
            pending = json.loads(other.read_bytes())
            if not pending['complete'] and Path(pending['payload']['root']) == Path(req['root']).resolve():
                raise Refused('registration-pending-request:'+other.stem)
        existing_tx = read(journal)
        if existing_tx:
            tx = json.loads(existing_tx)
            if tx['request_sha256'] != digest(encoded(req)):
                raise Refused('conflicting-duplicate')
            if digest(encoded(tx['payload'])) != tx['payload_sha256']:
                raise Refused('registration-journal-integrity')
            payload, result = tx['payload'], tx['result']
        else:
            payload, result = plan(bk, req)
            if result['preflight'] != req['preflight']:
                raise Refused('registration-stale-preflight')
            tx = {'request_sha256':digest(encoded(req)), 'payload':payload, 'payload_sha256':digest(encoded(payload)),
                  'result':result, 'complete':False}
        paths = [w['path'] for w in payload['writes']]+[a['path'] for a in payload['artifacts']]
        if payload.get('attachment'):
            paths.append(payload['attachment'])
        was_complete = tx['complete']
        with bk._resource_locks(paths, deadline):
            def guard():
                bk.ownership()
                if bk.control() != 'clear' or bk.config.get('recovery_only'):
                    raise Refused('cleanup-only')
                identity(bk, req)
                bk.check_claims(paths, caller['id'] if caller else '')
            guard()
            if not existing_tx:
                verify_observations(bk, payload)
                replace_preserving_permissions(journal, encoded(tx), None, guard)
                bk.fault('registration-after-journal')
            if not tx['complete']:
                # Inputs outside the write set still bind interrupted plans.
                expected_inventory = set(payload['stanza_inventory'])
                stanza_dir = bk.os_root/'memory/projects-ledger'
                expected_inventory.update(Path(w['path']).stem for w in payload['writes']
                                          if Path(w['path']).parent == stanza_dir and Path(w['path']).exists())
                current_inventory = {p.stem for p in stanza_dir.glob('*.md') if not p.name.startswith('_')}
                if current_inventory != expected_inventory:
                    raise Refused('registration-concurrent-change')
                changed_paths = {w['path'] for w in payload['writes']}
                for p, sha in payload['observed'].items():
                    if p not in changed_paths and hash_at(Path(p)) != sha:
                        raise Refused('registration-concurrent-change')
                # Verify the entire remaining plan before the next atomic write.
                for w in payload['writes']:
                    if hash_at(Path(w['path'])) not in {w['before'], w['after']}:
                        raise Refused('registration-concurrent-change')
                for a in payload['artifacts']:
                    if digest(stable(Path(a['path']))) != a['sha256']:
                        raise Refused('artifact-changing')
                for i,w in enumerate(payload['writes']):
                    path = Path(w['path'])
                    guard()
                    if hash_at(path) == w['after']:
                        continue
                    body = bytes.fromhex(w['body'])
                    if digest(body) != w['after']:
                        raise Refused('registration-journal-integrity')
                    for a in payload['artifacts']:
                        if digest(stable(Path(a['path']))) != a['sha256']:
                            raise Refused('artifact-changing')
                    replace_preserving_permissions(path, body, w['before'], guard)
                    if path == bk.config_path:
                        bk.config = json.loads(body)
                    bk.fault('registration-after-write:'+str(i))
                for a in payload['artifacts']:
                    if digest(stable(Path(a['path']))) != a['sha256']:
                        raise Refused('artifact-changing')
                tx['complete'] = True
                replace_preserving_permissions(journal, encoded(tx), hash_at(journal), guard)
            else:
                for w in payload['writes']:
                    if Path(w['path']) != bk.config_path and hash_at(Path(w['path'])) != w['after']:
                        raise Refused('registration-publication-drift')
        # Native admission uses the actual cwd and existing lifecycle writer.
        # Never admit the target by fabricating a target cwd from an OS-root task.
        bk = Bookkeeper(bk.config_path, clock=bk.clock, fault=bk.fault)
        caller = identity(bk, req)
        if caller is None:
            cwd = Path(req['workspace']).resolve()
            candidates = [(len(Path(p).resolve().parts), slug) for slug,v in bk.config['projects'].items()
                          for p in [v['root']]+v.get('worktrees',[]) if workspace_matches(v,cwd,Path(p))]
            if not candidates:
                raise Refused('native-cwd-not-selected')
            best = max(n for n,s in candidates)
            selected = {s for n,s in candidates if n == best}
            if len(selected) != 1:
                raise Refused('ambiguous-native-cwd')
            admission = bk.execute({'operation':'start', 'key':'registration-admit-'+digest(req['key'].encode()),
                'project':selected.pop(), 'native_id':req['native_id'], 'harness':req['harness'],
                'worktree':str(cwd), 'tab':req.get('tab','REG FLOW'), 'model':req.get('model','unavailable'),
                'task':'Register existing project '+payload['project']})
            caller = bk._session(admission['activation'])
        config = bk.config['projects'].get(payload['project'], {})
        if Path(config.get('root','')).resolve() != Path(payload['root']) or not config.get('provenance',True):
            raise Refused('registration-configuration-drift')
        if payload.get('attachment') and not any(workspace_matches(config, Path(payload['attachment']), Path(p))
                for p in [config['root']]+config.get('worktrees', [])):
            raise Refused('registration-configuration-drift')
        stanza = bk.os_root/'memory/projects-ledger'/(payload['project']+'.md')
        if not stanza.is_file() or Path(frontmatter(stanza.read_bytes()).get('path','')).resolve() != Path(payload['root']):
            raise Refused('registration-publication-drift')
        index = (bk.os_root/'memory/projects-ledger.md').read_text(encoding='utf-8-sig')
        if index.count('](projects-ledger/'+payload['project']+'.md)') != 1:
            raise Refused('registration-publication-drift')
        public = bk.coord/'sessions'/(caller['id']+'.md')
        if not public.is_file() or ('id: '+caller['id']) not in public.read_text(encoding='utf-8-sig'):
            raise Refused('registration-admission-publication-missing')
        # Exact bytes are verified on first/recovered publication. Later retries
        # allow independently authorized metadata edits; never restore old bytes.
        return {**result, 'effects':bool(payload['writes']) and not was_complete, 'duplicate':bool(existing_tx),
            'recovered':bool(existing_tx) and not was_complete,
            'configuration':'registered', 'ledger':'registered', 'public_publication':'verified',
            'admission':{'status':'active','activation':caller['id'],'project':caller['project'], 'workspace':caller['workspace'],
                         'target_project_admitted':caller['project'] == payload['project']},
            'host_receipt_delivery':'returned-to-cli; native-host-injection-unverified'}
