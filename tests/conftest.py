"""Model-free defaults. Remote checks require an explicit separate marker/run."""
import importlib.abc
import os
import socket
import sys

import pytest


class NoModelImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'transformers', 'faster_whisper', 'parler_tts', 'f5_tts', 'omnivoice'}:
            raise AssertionError('Model imports are forbidden in ordinary tests: '+fullname)
        return None


@pytest.fixture(autouse=True)
def isolate(monkeypatch, tmp_path, request):
    if request.node.get_closest_marker('models'):
        return
    monkeypatch.setenv('BVS_TEST_MODE', '1')
    monkeypatch.setenv('BVS_OFFLINE', '1')
    monkeypatch.setenv('HF_HUB_OFFLINE', '1')
    monkeypatch.setenv('TRANSFORMERS_OFFLINE', '1')
    monkeypatch.setenv('BVS_DATA_DIR', str(tmp_path/'state'))
    monkeypatch.setenv('BVS_MODEL_CACHE', str(tmp_path/'models'))
    guard = NoModelImports()
    sys.meta_path.insert(0, guard)
    original = socket.socket.connect
    def local_only(sock, address):
        if isinstance(address, tuple) and address[0] not in {'127.0.0.1', '::1', 'localhost'}:
            raise AssertionError('External networking is forbidden in ordinary tests')
        return original(sock, address)
    monkeypatch.setattr(socket.socket, 'connect', local_only)
    yield
    sys.meta_path.remove(guard)
