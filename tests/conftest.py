"""Model-free defaults. Remote checks require an explicit separate marker/run."""
import importlib.abc
import os
import socket
import selectors
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
    # Some managed sandboxes deny AF_UNIX send(), including asyncio's wakeup
    # socket. Poll only in that environment; do not change application I/O.
    reader, writer = socket.socketpair()
    try:
        writer.send(b'x')
    except PermissionError:
        original_select = selectors.DefaultSelector.select
        def bounded_select(selector, timeout=None):
            return original_select(selector, .01 if timeout is None else min(timeout, .01))
        monkeypatch.setattr(selectors.DefaultSelector, 'select', bounded_select)
    finally:
        reader.close()
        writer.close()
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
