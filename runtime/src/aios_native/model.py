"""Allowlisted native status-line model input; never creates lifecycle authority."""
import argparse
import json
from pathlib import Path
import sys
import uuid
from aios_core.store import WriterBusy
from .bookkeeping import Bookkeeper, Refused, digest, line


def observe(bk, payload):
    bk.ownership()
    native = line(payload['session_id'])
    model = line(payload['model']['id'])
    if not model or model == 'unavailable':
        raise Refused('native-model-missing')
    alias = bk.root/'aliases'/(digest(('claude-code:'+native).encode())+'.json')
    if not alias.is_file():
        raise Refused('native-activation-missing')
    state = bk._session(json.loads(alias.read_bytes())['activation'])
    if state['status'] != 'active' or state['harness'] != 'claude-code' or state['native_id'] != native:
        raise Refused('native-activation-not-active')
    if Path(payload['cwd']).resolve() != Path(state['workspace']).resolve():
        raise Refused('native-model-workspace-mismatch')
    if state['model'] == model and state.get('model_source') == 'claude-statusline':
        return model
    bk.execute({'operation':'checkpoint','key':'native-model-'+uuid.uuid4().hex,
                'activation':state['id'],'model':model,'model_source':'claude-statusline'})
    return model


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        model=observe(Bookkeeper(args.config),json.load(sys.stdin))
        print('AI OS | '+model)
    except (Refused,WriterBusy,OSError,ValueError,KeyError,TypeError):
        # Status-line delivery is metadata, never an admission or fallback path.
        print('AI OS | model pending')
    return 0
