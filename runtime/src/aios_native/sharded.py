"""Independent native journals, guarded shared resources, and durable close outboxes.

Selected only by project-session-v1 plus live-sharded/rehearsal-sharded mode.
Legacy binaries reject these modes. Flat activation/binding files retain existing
consumer contracts; each is owned by its activation/conversation. No global view
or event history is rewritten by a routine delivery.
"""
from __future__ import annotations

from contextlib import contextmanager, ExitStack
from datetime import datetime
import errno
import json
import os
import re
from pathlib import Path
import time

from aios_core.store import EventStore, WriterBusy, AppendResult
from aios_core.events import canonical_bytes, make_record, sha256_file
from aios_core.replay import _fold_line, CorruptLog
from aios_core.coord import snapshot
from aios_core.liveness import parse_session_frontmatter, interpret
from .bookkeeping import Bookkeeper, Refused, digest, encoded, claim_base, overlap, beneath, line, publication_retry
from .request_contract import validate_request, RequestInvalid

FORMAT = 'project-session-v1'


class NativeMutex:
    """Reuse the tested OS-lock protocol without allocating an event store."""
    _ensure_lock_file = EventStore._ensure_lock_file
    acquire_lock = EventStore.acquire_lock
    release_lock = EventStore.release_lock

    def __init__(self, path, *, direct=False):
        self.lock_path = path if direct else path/'.writer.lock'
        self.lock_timeout_seconds = 15.0
        self.lock_path.parent.mkdir(parents=True,exist_ok=True)
        self._ensure_lock_file()


def shared_read(path):
    deadline = time.monotonic()+.25
    while True:
        try:
            return path.read_bytes()
        except OSError as exc:
            # Windows CRT-backed open() can report sharing violations as
            # EACCES without winerror. Retry the read only, within the existing
            # budget; persistent denials still propagate unchanged.
            winerror = getattr(exc, 'winerror', None)
            retryable = (winerror in {5, 32, 33} or
                         (winerror is None and exc.errno == errno.EACCES))
            remaining = deadline - time.monotonic()
            if os.name != 'nt' or not retryable or remaining <= 0:
                raise
            time.sleep(min(.005, remaining))


class ProjectBookkeeper(Bookkeeper):
    sharded = True

    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)
        # Python's Windows long-path opt-in must not depend on a machine-wide
        # registry change. Native state paths use the Win32 extended prefix.
        if os.name == 'nt' and not str(self.root).startswith('\\\\?\\'):
            self.root = Path('\\\\?\\'+str(self.root))
            self.journal_root = self.root

    def ownership(self):
        current = json.loads(self.config_path.read_text(encoding='utf-8-sig'))
        if current != self.config or current.get('owner') != 'v2':
            raise Refused('ownership-changed')
        if not current.get('enabled', False):
            raise Refused('integration-disabled')
        if current.get('storage_format') != FORMAT:
            raise Refused('storage-format-mismatch')
        if current.get('mode') == 'rehearsal-sharded':
            sandbox = Path(current['rehearsal_root']).resolve()
            for p in [self.os_root, self.root] + [Path(x['root']) for x in current['projects'].values()]:
                if not beneath(p, sandbox):
                    raise Refused('rehearsal-path-outside-root')
        elif current.get('mode') != 'live-sharded':
            raise Refused('invalid-mode')
        if not isinstance(current.get('storage_generation'), str) or not current['storage_generation']:
            raise Refused('storage-generation-missing')

    def validate_claim_admission(self, claims):
        super().validate_claim_admission(claims)
        protected = [str(self.root), str(self.coord/'sessions')]
        for claim in claims:
            if any(overlap(claim, p, self.os_root) for p in protected):
                raise RequestInvalid('native-owned-resource-claim', 'claims[]')
            base = Path(claim_base(claim, self.os_root))
            if base.parent == (self.coord/'mailbox/operator').resolve() and base.name.endswith('-closeout.md'):
                raise RequestInvalid('native-owned-resource-claim', 'claims[]')

    def check_claims(self, paths, session_id=''):
        # Private activation state is authoritative even if its public row is
        # delayed or stale. A timeout never releases a live claim into new work.
        if not paths:
            return
        # Admission forbids claims on native-owned state and session records.
        # No foreign heartbeat must be opened to publish this activation's file.
        paths = [p for p in paths if not (beneath(Path(p),self.root)
                 or beneath(Path(p),self.coord/'sessions')
                 or (Path(p).parent == self.coord/'mailbox/operator' and Path(p).name.endswith('-closeout.md')))]
        if not paths:
            return
        known = set()
        directory = self.root/'active-index'
        if directory.exists():
            for p in directory.iterdir():
                if p.suffix != '.json' or not p.is_file():
                    continue
                marker = json.loads(shared_read(p))
                known.add(marker['id'])
                if marker['id'] == session_id:
                    continue
                possible = marker['claims'] + marker.get('previous_claims', [])
                if not any(overlap(c,target,self.os_root) for c in possible for target in paths):
                    continue
                state_path = self.root/'activations'/(marker['id']+'.json')
                state = json.loads(shared_read(state_path)) if state_path.exists() else marker
                if marker['id'] == session_id or state.get('status') == 'done':
                    continue
                claims = set(state.get('claims', [])) | set(marker['claims'])
                if any(overlap(c, target, self.os_root) for c in claims for target in paths):
                    raise Refused('claim-overlap:' + marker['id'])
        # Retain compatibility with independently owned legacy/advisory records.
        for p in (self.coord/'sessions').iterdir():
            if p.suffix != '.md' or not p.is_file():
                continue
            if p.stem in known or p.stem == session_id:
                continue
            facts = parse_session_frontmatter(shared_read(p).decode('utf-8-sig'), p.name)
            verdict = interpret(facts, self.clock())
            if verdict.id in known or verdict.id == session_id:
                continue
            if not facts.frontmatter_present:
                raise Refused('unreadable-session:' + p.name)
            if verdict.live and any(overlap(c, target, self.os_root) for c in verdict.claims for target in paths):
                raise Refused('claim-overlap:' + verdict.id)

    def _session(self, activation):
        if not re.fullmatch(r'[a-zA-Z0-9-]{1,120}',activation):
            raise Refused('invalid-activation')
        try:
            return json.loads(shared_read(self.root/'activations'/(activation+'.json')))
        except FileNotFoundError:
            raise Refused('activation-missing') from None

    def _scopes(self, paths):
        if not paths:
            return []
        domains = [(claim_base(str(self.os_root), self.os_root), 'os-infrastructure')]
        for slug, project in self.config['projects'].items():
            for root in [project['root']] + project.get('worktrees', []):
                domains.append((claim_base(root, self.os_root), 'project-' + digest(slug.encode())))
        scopes = set()
        for path in paths:
            target = claim_base(path, self.os_root)
            if beneath(Path(target), self.root):
                continue
            ancestors = [(len(root), scope) for root, scope in domains
                         if target == root or target.startswith(root + '/')]
            if ancestors:
                depth = max(n for n, _ in ancestors)
                scopes.update(scope for n, scope in ancestors if n == depth)
            else:
                # Unknown external paths still conflict conservatively by volume.
                scopes.add('external-' + digest(Path(target).anchor.casefold().encode()))
            # A broad parent intersects all configured child domains.
            scopes.update(scope for root, scope in domains if root.startswith(target + '/'))
        return sorted(scopes)

    @contextmanager
    def _lock(self, relative, deadline):
        direct = relative.startswith('requests/')
        store = NativeMutex(self.root/'locks'/(relative+'.lock' if direct else relative),direct=direct)
        remaining = max(0, deadline - time.monotonic())
        handle, token, _ = store.acquire_lock(timeout_seconds=remaining)
        try:
            yield
        finally:
            store.release_lock(handle, token)

    @contextmanager
    def _resource_locks(self, paths, deadline):
        with ExitStack() as stack:
            for scope in self._scopes(paths):
                stack.enter_context(self._lock('resources/'+scope, deadline))
            yield

    def _check_capacity(self, harness, exclude=''):
        view = snapshot(self.coord, self.clock())
        slots = view.slots.get(harness)
        if slots is None or slots.budget is None:
            raise Refused('harness-budget-unavailable-or-full')
        occupied = {v.id for v in view.verdicts if v.live and v.harness == harness and v.id != exclude}
        for marker_path in (self.root/'active-index').glob('*.json'):
            marker = json.loads(shared_read(marker_path))
            if marker['id'] == exclude:
                continue
            state_path = self.root/'activations'/(marker['id']+'.json')
            if state_path.exists():
                state = json.loads(shared_read(state_path))
                if (state['harness'] == harness and state['status'] == 'active'
                        and (self.clock()-datetime.fromisoformat(state['heartbeat'])).total_seconds() <= 3600):
                    occupied.add(state['id'])
            else:
                if 'harness' not in marker:
                    raise Refused('admission-reservation-unavailable')
                if marker['harness'] == harness:
                    occupied.add(marker['id'])
        if len(occupied) >= slots.budget:
            raise Refused('harness-budget-unavailable-or-full')

    def _plan(self, request):
        if request['operation'] in {'start','activate'}:
            self._check_capacity(request['harness'])
        # Fix the admission date to the journal route across a midnight boundary.
        old_clock = self.clock
        if getattr(self, '_request_stamp', None) is not None:
            self.clock = lambda: self._request_stamp
        self._closing_artifacts = request.get('artifacts', []) if request['operation'] == 'close' else []
        planned = {k: v for k, v in request.items() if k != 'artifacts'} if request['operation'] == 'close' else request
        try:
            result, writes, sid = super()._plan(planned)
            marker = self.root/'active-index'/(sid+'.json')
            if request['operation'] == 'close':
                if marker.exists():
                    writes.append(self._mut(marker, None))
            elif request['operation'] in {'start','activate'} or 'claims' in request:
                project = request.get('project') or self._session(sid)['project']
                previous = self._session(sid)['claims'] if request['operation'] not in {'start','activate'} else []
                # Publish reservations before alias/state writes. A crash makes
                # only these resources pending, never falsely unclaimed.
                writes.insert(0, self._mut(marker, encoded({'id':sid, 'project':project,
                                                           'claims':result['claims'],'previous_claims':previous,
                                                           'harness':request.get('harness') or self._session(sid)['harness']})))
            result['storage_format'] = FORMAT
            result['storage_generation'] = self.config['storage_generation']
            if request['operation'] == 'close':
                result['publication'] = 'pending'
            return result, writes, sid
        finally:
            self.clock = old_clock

    def _artifact_body(self, path):
        frozen = getattr(self, '_frozen_artifacts', None)
        return frozen[str(path.resolve())] if frozen is not None else path.read_bytes()

    def _closeout(self, root, state, req, date):
        frozen = {}
        artifacts = self._closing_artifacts
        # Validate actual containment before reading or persisting artifact bodies.
        for item in artifacts:
            path = (root/item['path']).resolve()
            if not beneath(path, root):
                raise Refused('artifact-outside-project')
            relative = path.relative_to(root)
            if ({p.casefold() for p in relative.parts} & {'inputs','background','.cowork','.git'}
                    or path in {root/'asset-registry.csv',root/'interaction-log.csv'}):
                raise Refused('artifact-readonly-or-bookkeeping')
            frozen[item['path']] = path.read_bytes().hex()
        if artifacts:
            state['assets'] = sorted(set(state.get('assets', [])) | {a['path'] for a in artifacts})
        state['publication_pending'] = True
        outbox = self.journal_root/'outbox'/('close-'+state['id']+'.json')
        if outbox.exists():
            raise Refused('closeout-name-collision')
        contribution = {'version': 1, 'state': state, 'request': req, 'date': date,
                        'artifacts': artifacts, 'frozen': frozen}
        return [self._mut(outbox, encoded(contribution))]

    def _pending_paths(self):
        paths = []
        for p in (self.journal_root/'pending').glob('*.json'):
            tx = json.loads(p.read_bytes())
            if not tx['complete']:
                paths.extend(w['path'] for w in tx['writes'])
                paths.extend(tx.get('resource_paths', []))
        return paths

    def _publish(self, tx, tx_path, *, cleanup=False):
        # Prepared intent is not a grant. After a crash, another holder may have
        # won before this activation state became visible. Recheck under the
        # same resource guards before replaying any state that grants claims.
        if tx['operation'] in {'start','activate'}:
            harness = 'codex-cli' if '-codex-v2-' in tx['activation'] else 'claude-code'
            self._check_capacity(harness, tx['activation'])
        self.check_claims(tx.get('claim_grants', []), tx['activation'])
        super()._publish(tx, tx_path, cleanup=cleanup)
        self._archive_transaction(tx, tx_path)

    def _archive_transaction(self, tx, path):
        self.ownership()
        target = self.journal_root/'transactions'/path.name
        target.parent.mkdir(exist_ok=True)
        if target.exists():
            if target.read_bytes()!=encoded(tx):
                raise Refused('completed-transaction-conflict')
            if path.exists():
                path.unlink()
            return
        self.ownership()
        # All bytes were fsynced as a complete journal before the same-volume
        # rename. Either name is a recoverable committed result after a crash.
        def verify():
            self.ownership()
            if path.read_bytes()!=encoded(tx) or target.exists():
                raise Refused('transaction-archive-conflict')
        publication_retry(lambda:os.replace(path,target),check=verify,
            deadline=self._publication_deadline or time.monotonic()+.5,role='transaction')

    def _reconcile(self):
        directory=self.journal_root/'pending'
        if not directory.exists():
            return
        for path in sorted(directory.glob('*.json')):
            tx=json.loads(path.read_bytes())
            if digest(encoded(tx['writes']))!=tx['plan_sha256']:
                raise Refused('journal-integrity-failed')
            if tx['complete']:
                self._archive_transaction(tx,path)
            else:
                self._publish(tx,path,cleanup=True)

    def _event(self, tx, phase):
        # Same verified kernel records and blob/hash-chain contract, with one
        # verified state load per locked native transaction instead of five.
        store=EventStore(self.journal_root/'events')
        caches=getattr(self,'_event_cache',{})
        self._event_cache=caches
        cache_key=str(store.root)
        handle,token,wait=store.acquire_lock()
        try:
            identity=store.events_path.stat() if store.events_path.exists() else None
            signature=None if identity is None else (identity.st_dev,identity.st_ino,identity.st_size,identity.st_mtime_ns,identity.st_ctime_ns)
            cached=caches.get(cache_key)
            state=cached[1] if cached and cached[0]==signature else store.state()
            removed=store._truncate_torn_tail(state)
            state.trailing_bytes=0
            key=tx['key']+':'+phase
            payload={'operation':tx['operation'],'phase':phase,'request_sha256':tx['request_sha256'],
                     'plan_sha256':tx['plan_sha256'],'files':len(tx['writes'])}
            payload_hash=digest(canonical_bytes(payload))
            existing=state.commands.get(key)
            if existing is not None:
                if (existing.aggregate_id!=tx['activation'] or existing.event_type!='native.bookkeeping.'+phase
                        or existing.payload_sha256!=payload_hash):
                    raise Refused('event-duplicate-conflict')
                return AppendResult('duplicate',existing.event_id,existing.sequence,existing.aggregate_version,
                                    payload_hash,False,wait,removed)
            payload_hash,created=store.publish_blob(payload)
            current=state.aggregates.get(tx['activation'])
            record=make_record(aggregate_id=tx['activation'],aggregate_version=current.version+1 if current else 1,
                command_id=key,event_type='native.bookkeeping.'+phase,payload_sha256=payload_hash,
                previous_event_id=state.head_event_id,sequence=state.last_sequence+1)
            line_bytes=canonical_bytes(record)
            with store.events_path.open('ab',buffering=0) as stream:
                stream.write(line_bytes+b'\n');os.fsync(stream.fileno())
            _fold_line(state,line_bytes,state.last_sequence+1,store.blobs_path)
            state.byte_offset+=len(line_bytes)+1
            state.prefix_sha256=sha256_file(store.events_path)
            identity=store.events_path.stat()
            caches[cache_key]=((identity.st_dev,identity.st_ino,identity.st_size,identity.st_mtime_ns,identity.st_ctime_ns),state)
            result=AppendResult('committed',record['event_id'],record['sequence'],record['aggregate_version'],
                                payload_hash,created,wait,removed)
        finally:
            store.release_lock(handle,token)
        if phase=='committed' and (state.last_sequence%64==0 or tx['operation']=='close'):
            from aios_core.checkpoints import write_checkpoint,prune_checkpoints
            write_checkpoint(store,state);prune_checkpoints(store,keep=2)
        return result

    def _duplicate(self, tx, request):
        if tx['request_sha256'] != digest(encoded(request)):
            raise Refused('conflicting-duplicate')
        state = self._session(tx['activation'])
        if request['operation'] != 'close':
            if state['status'] != 'active':
                raise Refused('activation-closed')
            self.check_claims(state['claims'], state['id'])
        result = dict(tx['result'])
        result['claims'] = state['claims']
        if request['operation'] in {'start','activate','resume'}:
            result['working_tree'] = self.work_state({'root': state['workspace']})
        result.update(duplicate=True, controls=self.control(), storage_format=FORMAT,
                      storage_generation=self.config['storage_generation'])
        return result

    def _route(self, request):
        if request['operation'] in {'start','activate'}:
            project = request['project']
            sid = self._request_stamp.strftime('%Y%m%d')+'-'+request['harness'].split('-')[0]+'-v2-'+digest(
                (self.config['epoch']+':'+request['key']).encode())[:16]
        else:
            state = self._session(request['activation'])
            project, sid = state['project'], state['id']
        if project not in self.config['projects']:
            raise Refused('project-not-selected')
        return self.root/'projects'/digest(project.encode())/'sessions'/sid, sid

    def execute(self, request, *, lock_timeout_seconds=20):
        self.ownership()
        validate_request(request)
        self.validate_claim_admission(request.get('claims', []))
        self.validate_artifact_paths(request.get('artifacts', []))
        if self.config.get('recovery_only') and request['operation'] not in {'close','reconcile'}:
            raise Refused('cleanup-only:recovery-runtime')
        if request['operation'] == 'reconcile':
            return self._reconcile_all(lock_timeout_seconds)
        self._request_stamp = self.clock()
        self._event_cache = {}
        started = time.monotonic()
        deadline = started + lock_timeout_seconds
        self._publication_deadline = deadline + .5
        op = request['operation']
        key_hash = digest(request['key'].encode())
        phase = 'lock-wait'
        acquired = None
        try:
            # This lock is per request identity, never a global admission queue.
            with self._lock('requests/'+key_hash, deadline):
                legacy = self.root/'transactions'/(key_hash+'.json')
                if legacy.exists():
                    tx = json.loads(legacy.read_bytes())
                    if not tx['complete']:
                        raise Refused('legacy-migration-incomplete')
                    if self.control() != 'clear' and op != 'close':
                        raise Refused('cleanup-only:'+self.control())
                    return self._duplicate(tx, request)
                route, sid = self._route(request)
                index = self.root/'request-index'/(key_hash+'.json')
                expected = {'request_sha256': digest(encoded(request)), 'journal': str(route), 'activation': sid,
                            'stamp': self._request_stamp.isoformat()}
                if index.exists():
                    recorded = json.loads(index.read_bytes())
                    if recorded['request_sha256'] != expected['request_sha256']:
                        raise Refused('conflicting-duplicate')
                    route, sid = Path(recorded['journal']), recorded['activation']
                    self._request_stamp = datetime.fromisoformat(recorded['stamp'])
                    if not beneath(route, self.root/'projects'):
                        raise Refused('request-index-integrity-failed')
                self.journal_root = route
                route.mkdir(parents=True, exist_ok=True)
                with ExitStack() as stack:
                    if op in {'start','activate'}:
                        binding = digest((request['harness']+':'+request['native_id']).encode())
                        stack.enter_context(self._lock('bindings/'+binding, deadline))
                    # A fresh resume is infrequent; admission capacity is checked
                    # under the harness lock, never on ordinary fresh heartbeats.
                    if op in {'start','activate','resume'}:
                        harness = request.get('harness') or self._session(sid)['harness']
                        stack.enter_context(self._lock('admission/'+harness, deadline))
                    mutex = NativeMutex(route/'mutex')
                    handle, token, _ = mutex.acquire_lock(timeout_seconds=max(0, deadline-time.monotonic()))
                    stack.callback(mutex.release_lock, handle, token)
                    acquired = time.monotonic()
                    self.ownership()
                    controls = self.control()
                    if op != 'close' and controls != 'clear':
                        raise Refused('cleanup-only:'+controls)
                    current = None
                    if op not in {'start','activate'}:
                        current = self._session(sid)
                        if current['epoch'] != self.config['epoch']:
                            raise Refused('activation-epoch-mismatch')
                        age = (self.clock()-datetime.fromisoformat(current['heartbeat'])).total_seconds()
                        if age > 3600 and op == 'checkpoint':
                            raise Refused('fresh-resume-required')
                        if op == 'resume' and age > 3600:
                            self._check_capacity(current['harness'], sid)
                    paths = self._pending_paths()
                    if 'claims' in request or op == 'close':
                        paths += request.get('claims', []) + (current['claims'] if current else [])
                    if request.get('artifacts') and op != 'close':
                        project = self.config['projects'][current['project'] if current else request['project']]
                        paths.append(project['root'])
                    with self._resource_locks(paths, deadline):
                        phase = 'reconciliation'
                        self._reconcile()
                        tx_path = route/'pending'/(key_hash+'.json')
                        completed = route/'transactions'/(key_hash+'.json')
                        if completed.exists():
                            result = self._duplicate(json.loads(completed.read_bytes()), request)
                        else:
                            phase = 'planning'
                            result, writes, actual_sid = self._plan(request)
                            if actual_sid != sid:
                                raise Refused('activation-route-mismatch')
                            self.check_claims([w['path'] for w in writes], sid)
                            tx = {'key': request['key'], 'operation': op, 'activation': sid,
                                  'request_sha256': digest(encoded(request)), 'writes': writes,
                                  'plan_sha256': digest(encoded(writes)), 'complete': False, 'result': result,
                                  'resource_paths':paths, 'claim_grants':request.get('claims', [])}
                            if not index.exists():
                                self._atomic(index, encoded(expected))
                            self._atomic(tx_path, encoded(tx))
                            self.fault('after-journal')
                            phase = 'publication'
                            self._publish(tx, tx_path)
                            result = {**result, 'duplicate': False, 'controls': controls}
                if op == 'close':
                    result['publication'] = self._flush_close(sid, deadline+.5)
                return result
        except CorruptLog:
            raise Refused('event-integrity-failed') from None
        except WriterBusy as exc:
            exc.native_writer_phase = phase
            exc.native_lock_wait_ms = (time.monotonic()-started)*1000 if acquired is None else (acquired-started)*1000
            exc.native_lock_held_ms = 0 if acquired is None else (time.monotonic()-acquired)*1000
            raise
        finally:
            self._publication_deadline = None

    def _flush_close(self, sid, deadline):
        base = self.journal_root
        outbox = base/'outbox'/('close-'+sid+'.json')
        try:
            mutex = NativeMutex(base/'mutex')
            handle, token, _ = mutex.acquire_lock(timeout_seconds=max(0, min(.05, deadline-time.monotonic())))
            try:
                self.ownership()
                state = self._session(sid)
                if state['status'] != 'done':
                    raise Refused('close-not-terminal')
                root = Path(self.config['projects'][state['project']]['root']).resolve()
                with self._resource_locks([str(root)], min(deadline, time.monotonic()+.05)):
                    self.journal_root = base/'publication'
                    self.journal_root.mkdir(exist_ok=True)
                    self._reconcile()
                    if not outbox.exists():
                        return 'complete' if not self._session(sid).get('publication_pending') else 'pending'
                    if time.monotonic() >= deadline:
                        return 'pending'
                    contribution = json.loads(outbox.read_bytes())
                    self._frozen_artifacts = {str((root/k).resolve()): bytes.fromhex(v)
                                              for k, v in contribution['frozen'].items()}
                    writes = []
                    if contribution['artifacts']:
                        writes += super()._assets(root, contribution['state'], contribution['artifacts'], contribution['date'])
                    writes += super()._closeout(root, contribution['state'], contribution['request'], contribution['date'])
                    state['publication_pending'] = False
                    writes += [self._mut(self.root/'activations'/(sid+'.json'), encoded(state)), self._mut(outbox, None)]
                    self.check_claims([w['path'] for w in writes], sid)
                    key = 'project-close-'+sid
                    tx_path = self.journal_root/'pending'/(digest(key.encode())+'.json')
                    tx = {'key':key, 'operation':'close', 'activation':sid,
                          'request_sha256':digest(encoded(contribution)), 'writes':writes,
                          'plan_sha256':digest(encoded(writes)), 'complete':False,
                          'result':{'status':'closed','activation':sid,'publication':'complete'}}
                    self._atomic(tx_path, encoded(tx))
                    self._publish(tx, tx_path, cleanup=True)
                    return 'complete'
            finally:
                mutex.release_lock(handle, token)
        except (WriterBusy, Refused, OSError, ValueError, KeyError):
            # Terminal local intent and the exact durable outbox are already
            # committed. A delayed project publication is explicitly pending.
            return 'pending'
        finally:
            self.journal_root = base
            self._frozen_artifacts = None

    def publication_status(self, project_id, limit=1000):
        """Bounded, non-atomic observation; never expose frozen artifact bodies."""
        result = {'pending_activations': [], 'complete': True,
                  'observed_at': self.clock().isoformat(), 'atomic': False}
        try:
            directory = self.root/'projects'/digest(project_id.encode())/'sessions'
            if directory.exists():
                for number, session in enumerate(directory.iterdir()):
                    if number >= limit:
                        result['complete'] = False
                        result['reason'] = 'session-observation-limit'
                        break
                    if (session/'outbox'/('close-'+session.name+'.json')).exists():
                        result['pending_activations'].append(session.name)
        except OSError:
            result['complete'] = False
            result['reason'] = 'publication-observation-unavailable'
        return result

    def _reconcile_all(self, timeout):
        # Explicit operator recovery only. Routine hooks never enumerate other journals.
        deadline = time.monotonic()+timeout
        pending = []
        for directory in sorted((self.root/'projects').glob('*/sessions/*')):
            sid = directory.name
            self.journal_root = directory
            if time.monotonic() >= deadline:
                pending.append(sid)
                continue
            try:
                mutex = NativeMutex(directory/'mutex')
                h, t, _ = mutex.acquire_lock(timeout_seconds=min(.05, max(0, deadline-time.monotonic())))
                try:
                    with self._resource_locks(self._pending_paths(), min(deadline,time.monotonic()+.05)):
                        self._reconcile()
                finally:
                    mutex.release_lock(h,t)
                if (directory/'outbox'/('close-'+sid+'.json')).exists() and self._flush_close(sid,deadline) != 'complete':
                    pending.append(sid)
            except (WriterBusy, Refused, CorruptLog, OSError, ValueError, KeyError):
                pending.append(sid)
        return {'status':'reconciled' if not pending else 'reconciliation-pending',
                'pending_activations':pending, 'controls':self.control(), 'storage_format':FORMAT}
