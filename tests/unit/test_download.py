import hashlib
import json
from dataclasses import replace

import pytest

from bvs.contracts import RunContext
from bvs.download import download_model, engine_view, local_model_path
from bvs.errors import BVSError
from bvs.registry import get_spec


def test_planned_and_missing_are_metadata_only(tmp_path):
    assert engine_view(get_spec('voxcpm2-bn'), tmp_path, offline=True)['availability'] == 'planned'
    assert engine_view(get_spec('dummy'), tmp_path, offline=True)['availability'] == 'ready'
    assert engine_view(get_spec('mms'), tmp_path, offline=True)['availability'] == 'extra_missing'


def test_local_manifest_checks_identity_hashes_and_closure(tmp_path):
    spec = replace(get_spec('mms'), model_revision='a'*40)
    snapshot = tmp_path/'snapshots'/'mms'
    snapshot.mkdir(parents=True)
    files = {}
    for name in ('config.json', 'tokenizer_config.json', 'vocab.json', 'model.safetensors'):
        (snapshot/name).write_bytes(b'test')
        files[name] = {'bytes':4, 'sha256':hashlib.sha256(b'test').hexdigest()}
    selection = tmp_path/'selections'/'mms.json'
    selection.parent.mkdir()
    manifest = {'model_id':spec.model_id, 'revision':spec.model_revision, 'path':'snapshots/mms', 'files':files}
    selection.write_text(json.dumps(manifest))
    assert local_model_path(spec,tmp_path) == snapshot
    (snapshot/'vocab.json').write_bytes(b'bad!')
    with pytest.raises(BVSError) as exc:
        local_model_path(spec,tmp_path)
    assert exc.value.code == 'MODEL_INCOMPLETE'
    manifest['path'] = '../escape'
    selection.write_text(json.dumps(manifest))
    with pytest.raises(BVSError):
        local_model_path(spec,tmp_path)


def test_offline_download_refused_before_import(tmp_path):
    with pytest.raises(BVSError) as exc:
        download_model(get_spec('mms'),tmp_path,RunContext(lambda _:None,lambda:False))
    assert exc.value.code == 'OFFLINE'
