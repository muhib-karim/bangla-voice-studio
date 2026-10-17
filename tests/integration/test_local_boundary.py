from fastapi.testclient import TestClient

from bvs.config import Settings
from bvs.web.app import create_app


def test_auth_host_origin_csrf_and_health(tmp_path):
    settings=Settings(data_dir=tmp_path,model_cache_dir=tmp_path/'models',demo=True,api_token='long-local-test-token')
    with TestClient(create_app(settings)) as client:
        assert client.get('/health').status_code==200
        assert client.get('/api/v1/engines').status_code==401
        headers={'Authorization':'Bearer long-local-test-token'}
        assert client.get('/api/v1/engines',headers=headers).status_code==200
        assert client.get('/api/v1/engines',headers={**headers,'Host':'evil.example'}).status_code==403
        assert client.post('/api/v1/normalizations',json={'text':'1'},headers={**headers,'Origin':'https://evil.example'}).status_code==403
        client.get('/',headers=headers)
        assert client.post('/api/v1/normalizations',json={'text':'1'},headers={**headers,'Origin':'http://testserver'}).status_code==403
        csrf=client.cookies['bvs_csrf']
        assert client.post('/api/v1/normalizations',json={'text':'1'},headers={**headers,'Origin':'http://testserver','X-CSRF-Token':csrf}).status_code==200
        assert client.get('/api/v1/engines',auth=('bvs','long-local-test-token')).status_code==200


def test_no_input_echo_and_unsupported_idempotency(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path,model_cache_dir=tmp_path/'models',demo=True))) as client:
        response=client.post('/api/v1/normalizations',json={'text':{'secret':'do-not-echo'}})
        assert response.status_code==422
        assert 'do-not-echo' not in response.text
        assert client.post('/api/v1/normalizations',json={'text':'1'},headers={'Idempotency-Key':'bad'}).status_code==400
        assert client.get('/api/v1/artifacts/../../etc/passwd').status_code==404
