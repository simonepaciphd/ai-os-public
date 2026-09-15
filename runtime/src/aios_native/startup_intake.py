"""Bounded, read-only startup indexes; never receipt attestation or write authority."""
from __future__ import annotations
import base64
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from aios_core.coord import parse_closeout_note
from aios_core.liveness import parse_session_frontmatter, interpret, parse_budgets, slot_report
from .bookkeeping import Bookkeeper, Refused, digest, overlap, workspace_matches

VERSION = 'native-startup-intake-v2'
MAX_BYTES = 65536
MAX_BOARD_BYTES = 1048576
MAX_ENTRIES = 4096
MAX_SESSIONS = 256

def _revision(path: Path):
    """Observable identity/metadata; never a lock, capability or atomic snapshot."""
    if path.is_symlink() or path.is_junction():
        raise Refused('intake-linked-source')
    s = path.stat()
    return (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns,
            s.st_ctime_ns, getattr(s, 'st_birthtime_ns', None))

def _bounded(path: Path, limit: int = MAX_BYTES) -> bytes:
    with path.open('rb') as stream:
        body = stream.read(limit + 1)
    if len(body) > limit:
        raise Refused('intake-source-too-large')
    return body

def _entries(directory: Path, limit: int):
    """Never recurse or choose an arbitrary truncated page from an unsorted scan."""
    entries = []
    with os.scandir(directory) as scan:
        for entry in scan:
            if len(entries) >= limit:
                raise Refused('intake-index-overflow')
            if entry.is_symlink() or Path(entry.path).is_junction():
                raise Refused('intake-linked-source')
            entries.append(Path(entry.path))
    return sorted(entries, key=lambda p: p.name)

def _safe_code(exc):
    if isinstance(exc, Refused) and str(exc) in {
        'intake-source-too-large','intake-index-overflow','intake-linked-source'}:
        return str(exc)
    return 'source-missing' if isinstance(exc, FileNotFoundError) else 'source-unreadable'

def collect(bk: Bookkeeper, *, native_id: str, harness: str, cwd: Path,
            recipient: str = 'operator', page_size: int = 32, cursor: str | None = None,
            history: bool = False) -> dict:
    if not isinstance(native_id, str) or not native_id or len(native_id)>256:
        raise Refused('native-identity-missing')
    if harness not in {'codex-cli','claude-code'} or not re.fullmatch(r'[A-Za-z0-9_-]{1,120}', recipient):
        raise Refused('invalid-intake-arguments')
    if type(page_size) is not int or not 1 <= page_size <= 128:
        raise Refused('invalid-intake-page-size')
    bk.ownership()
    alias = bk.root / 'aliases' / (digest((harness+':'+native_id).encode())+'.json')
    try:
        activation = json.loads(_bounded(alias))['activation']
    except FileNotFoundError:
        raise Refused('native-not-yet-admitted') from None
    state = bk._session(activation)
    if state['native_id'] != native_id or state['harness'] != harness:
        raise Refused('native-identity-mismatch')
    if state['status'] != 'active':
        raise Refused('explicit-activation-required')
    if Path(state['workspace']).resolve() != cwd.resolve():
        raise Refused('native-cwd-not-selected')
    project=bk.config['projects'][state['project']]
    if not any(workspace_matches(project,cwd,Path(p)) for p in [project['root']]+project.get('worktrees',[])):
        raise Refused('native-cwd-not-selected')
    now=bk.clock()
    heartbeat=datetime.fromisoformat(state['heartbeat'])
    if heartbeat.tzinfo is None or not -300 <= (now-heartbeat).total_seconds() <= 3600:
        raise Refused('stale-native-receipt')
    controls=bk.control()
    result=dict(version=VERSION, observed_at=now.isoformat(), activation=activation,
        project=state['project'], canonical_run={'availability':'unavailable','value':None},
        controller_version='native-bookkeeping-existing', package_sha256=digest(Path(__file__).read_bytes()),
        controls=controls, read_only=True, write_authority=False, archive_advanced=False,
        next_action='read decision-bearing indexed notes; propose phases 1-4; phase 5 approval required',
        sources={}, errors=[], entries=[], complete=False, continuation_cursor=None,
        startup_cursor={'availability':'unavailable','value':None,'reason':'no selected durable intake cursor in native configuration'},
        history_scope='explicit closed-session recovery index' if history else 'unread mailbox and inbox; closed history excluded',
        launch_authority=False)
    reads = {}
    directories = {}
    lazy_absent = set()
    def changed(relative):
        result['errors'].append({'source':relative,'code':'source-changed-during-read'})
        if relative in result['sources']: result['sources'][relative]['complete']=False
    def listing(relative, limit):
        path=bk.coord/relative
        try:
            before=_revision(path)
        except FileNotFoundError:
            if not relative.startswith('mailbox/'):
                raise
            # SPEC mailboxes are created lazily. A missing recipient is empty;
            # a missing/unreadable mailbox root is still a coordination failure.
            _revision(bk.coord/'mailbox')
            if not (bk.coord/'mailbox').is_dir(): raise NotADirectoryError()
            lazy_absent.add(relative)
            return []
        paths=_entries(path,limit)
        revisions=[(p.name,_revision(p)) for p in paths]
        directories[relative]=(limit,before,revisions)
        if before!=_revision(path): changed(relative)
        return paths
    def source(relative):
        try:
            path=bk.coord/relative
            if not path.resolve().is_relative_to(bk.coord.resolve()): raise Refused('intake-linked-source')
            before=_revision(path)
            body=_bounded(path, MAX_BOARD_BYTES if relative=='BOARD.md' else MAX_BYTES)
            reads[relative]=(before,digest(body))
            result['sources'][relative]={'availability':'observed','sha256':digest(body),'bytes':len(body),'revision':before,'complete':True}
            if before!=_revision(path): changed(relative)
            try:
                text=body.decode('utf-8-sig',errors='strict')
                encoding='utf-8'
            except UnicodeDecodeError:
                # Historical Windows PowerShell notes may predate UTF-8.
                # Keep raw-byte hashes and explicitly identify the fallback;
                # never rewrite a note or discard undecodable bytes.
                if not relative.startswith('mailbox/'):
                    raise
                if body.startswith((b'\xff\xfe',b'\xfe\xff')):
                    text=body.decode('utf-16',errors='strict'); encoding='utf-16-bom'
                else:
                    text=body.decode('cp1252',errors='strict'); encoding='windows-1252-legacy-fallback'
                result.setdefault('warnings',[]).append({'source':relative,'code':'legacy-note-encoding','encoding':encoding})
            result['sources'][relative]['encoding']=encoding
            return text
        except (OSError, ValueError, Refused) as exc:
            code=_safe_code(exc)
            result['sources'][relative]={'availability':'unavailable','sha256':None,'complete':False,'error':code}
            result['errors'].append({'source':relative,'code':code})
            return None
    spec=source('SPEC.md'); source('BOARD.md')
    facts=[]; session_complete=True
    try:
        paths=listing('sessions', MAX_SESSIONS)
        for p in paths:
            if p.is_file() and p.suffix=='.md':
                text=source('sessions/'+p.name)
                if text is None: session_complete=False;continue
                f=parse_session_frontmatter(text,p.name);facts.append(f)
                if not f.frontmatter_present: session_complete=False
    except (OSError,Refused) as exc:
        session_complete=False
        result['errors'].append({'source':'sessions','code':_safe_code(exc)})
    verdicts=[interpret(f,now) for f in facts]
    result['slots']={'availability':'observed' if session_complete and spec else 'unavailable',
        'value':{k:v.as_dict() for k,v in slot_report(verdicts,parse_budgets(spec)).items()} if session_complete and spec else None}
    result['relevant_claim_conflicts']={'availability':'observed' if session_complete else 'unavailable',
        'value':[{'holder':v.id,'source':'sessions/'+v.source} for v in verdicts if v.live and v.id!=activation
            and any(overlap(a,b,bk.os_root) for a in v.claims for b in state['claims'])] if session_complete else None}
    if not session_complete: result['errors'].append({'source':'sessions','code':'incomplete-session-coverage'})
    if controls!='clear': result['errors'].append({'source':'control','code':controls})
    dirs=['mailbox/'+recipient,'mailbox/'+activation,'inbox']
    if history: dirs.append('sessions/_closed')
    records=[]
    for directory in sorted(set(dirs)):
        try:
            paths=listing(directory,MAX_ENTRIES)
            for p in paths:
                if not p.is_file() or p.name.startswith('_') or p.name=='README.md': continue
                stat=p.stat()
                records.append((directory+'/'+p.name,stat.st_size,stat.st_mtime_ns))
            result['sources'][directory]={'availability':'observed','complete':True,'indexed_files':sum(r[0].startswith(directory+'/') for r in records)}
        except (OSError,Refused) as exc:
            result['errors'].append({'source':directory,'code':_safe_code(exc)})
            result['sources'][directory]={'availability':'unavailable','complete':False}
    records.sort()
    # Bind every page to the same source identities/revisions and exact query.
    # Index metadata covers unreturned files without reading all note bodies.
    # Session heartbeats necessarily change between hook-driven page requests.
    # Recheck sessions/controls on every page, but bind pagination to the intake
    # corpus rather than those live observations. Note/inbox edits still stale
    # the chain. Each page's capacity and claims describe its own observed_at.
    stable_directories={k:v for k,v in directories.items() if k!='sessions'}
    stable_reads={k:v for k,v in reads.items() if not k.startswith('sessions/')}
    binding=digest(json.dumps([VERSION,str(bk.coord.resolve()),str(cwd.resolve()),
        activation,state['project'],harness,recipient,history,page_size,records,
        stable_directories,stable_reads,sorted(lazy_absent)],ensure_ascii=True,sort_keys=True).encode())
    offset=0
    if cursor:
        try:
            if len(cursor)>1024: raise ValueError()
            token=json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
            if set(token)!={'binding','offset'} or token['binding']!=binding or type(token['offset']) is not int or not 0<=token['offset']<=len(records):
                raise ValueError()
            offset=token['offset']
        except (ValueError,TypeError,KeyError):
            raise Refused('intake-cursor-stale-or-invalid') from None
    for relative,size,mtime in records[offset:offset+page_size]:
        item={'reference':relative,'bytes':size,'revision_mtime_ns':mtime,'body_included':False}
        text=source(relative)
        if text is not None:
            item['sha256']=result['sources'][relative]['sha256']
            try:
                stat=(bk.coord/relative).stat()
                if (stat.st_size,stat.st_mtime_ns)!=(size,mtime): changed(relative)
            except OSError: changed(relative)
            if relative.startswith('mailbox/'):
                note=parse_closeout_note(text,relative)
                item.update(kind='closeout' if note.is_closeout else 'legacy-or-message',metadata_valid=note.valid,
                    missing=list(note.missing),decision_points=note.decision_points,
                    requires_context_read=True)
            else: item.update(kind='brief' if relative.startswith('inbox/') else 'closed-session',requires_context_read=True)
        else: item.update(kind='unavailable',requires_context_read=True)
        result['entries'].append(item)
    next_offset=offset+len(result['entries'])
    # One bounded revalidation pass. No retry/restart that can skip unseen notes.
    # Changes after this pass remain possible: this is deliberately non-atomic.
    for relative,(revision,body_hash) in reads.items():
        try:
            path=bk.coord/relative
            if _revision(path)!=revision or digest(_bounded(path, MAX_BOARD_BYTES if relative=='BOARD.md' else MAX_BYTES))!=body_hash or _revision(path)!=revision:
                changed(relative)
        except (OSError,Refused): changed(relative)
    for relative in lazy_absent:
        try:
            _revision(bk.coord/'mailbox')
            _revision(bk.coord/relative)
        except FileNotFoundError:
            if not (bk.coord/'mailbox').is_dir(): changed(relative)
        except (OSError,Refused): changed(relative)
        else: changed(relative)
    for relative,(limit,revision,entries) in directories.items():
        try:
            path=bk.coord/relative
            if (_revision(path)!=revision or
                [(p.name,_revision(p)) for p in _entries(path,limit)]!=entries or
                _revision(path)!=revision): changed(relative)
        except (OSError,Refused): changed(relative)
    if any(e['code']=='source-changed-during-read' for e in result['errors']):
        result['slots']={'availability':'unavailable','value':None}
        result['relevant_claim_conflicts']={'availability':'unavailable','value':None}
    if not result['errors'] and next_offset<len(records):
        result['continuation_cursor']=base64.urlsafe_b64encode(json.dumps({'binding':binding,'offset':next_offset}).encode()).decode()
    result['coverage']={'index_revision_sha256':binding,'index_records':len(records),'offset':offset,
        'returned':len(result['entries']),'file_byte_limit':MAX_BYTES,'board_byte_limit':MAX_BOARD_BYTES,'directory_entry_limit':MAX_ENTRIES,
        'live_session_observations':'refreshed independently on every page; excluded from corpus cursor binding',
        'session_entry_limit':MAX_SESSIONS,'index_is_snapshot':False,
        'revalidation_passes':1,'page_chain_valid':not result['errors'],
        'revision_limit':'Observable identity/metadata and read-body hashes; changes after checks or indistinguishable ABA are not excluded.'}
    if result['errors']:
        result['next_action']='Coverage uncertain; preserve decisions and do not advance/archive. For source-changed-during-read, restart after sources stabilize. For missing/unreadable/oversized sources or overflow, report the exact source and repair that condition; repeating an unchanged collection cannot clear it. Historical overflow recovery remains unavailable pending U1.'
    result['page_complete']=not result['errors']
    result['complete']=not result['errors'] and result['continuation_cursor'] is None and offset==0
    result['mode']='normal-read-only' if result['complete'] else 'degraded'
    result['brief_policy']='All non-README/non-underscore files remain candidates; absent brief: ask if interactive; auto-launched checks every 5 minutes up to 60 minutes then reports absence. Collector never polls, consumes or renames.'
    bk.ownership()
    if bk.control()!=controls: raise Refused('intake-controls-changed')
    if hasattr(bk, "publication_status"):
        result["project_publication"] = bk.publication_status(state["project"])
    return result
