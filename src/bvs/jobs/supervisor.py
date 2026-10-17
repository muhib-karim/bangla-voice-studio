"""One process per job, with an exclusive state-directory lock."""
from __future__ import annotations

import fcntl
import json
import os
import select
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

from bvs.config import Settings
from bvs.download import atomic_json
from bvs.errors import BVSError
from bvs.jobs.store import Store


class Supervisor:
    def __init__(self, store: Store, settings: Settings, prepare: Callable[[dict[str, Any]], dict[str, Any]]):
        self.store, self.settings, self.prepare = store, settings, prepare
        self.lock: TextIO | None = None
        self.thread: threading.Thread | None = None
        self.stopping = threading.Event()
        self.process: subprocess.Popen[str] | None = None

    def start(self) -> None:
        self.lock = (self.store.directory / 'worker.lock').open('a+')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self.lock.close()
            self.lock = None
            raise BVSError('WORKER_LOCKED', 'State directory is in use; connect to the running server with --server URL') from exc
        self.store.recover()
        self.stopping.clear()
        self.thread = threading.Thread(target=self._loop, name='bvs-supervisor', daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stopping.set()
        if self.thread:
            self.thread.join(timeout=10)
        if self.process and self.process.poll() is None:
            self._signal(signal.SIGKILL)
            self.process.wait(timeout=2)
        if self.lock:
            fcntl.flock(self.lock, fcntl.LOCK_UN)
            self.lock.close()
            self.lock = None

    def _signal(self, sig: int) -> None:
        if self.process:
            try:
                os.killpg(self.process.pid, sig)
            except ProcessLookupError:
                pass

    def _loop(self) -> None:
        while not self.stopping.is_set():
            jobs = self.store.list(state='queued')
            if not jobs:
                self.stopping.wait(.05)
                continue
            job = jobs[0]
            try:
                self._run(job)
            except Exception:
                # Do not echo worker inputs, paths or third-party exception strings.
                current = self.store.get(job['id'])
                if current['state'] == 'running':
                    self.store.transition(job['id'], 'failed', error=dict(code='WORKER_FAILED', message='Worker failed; retry the job', details=[], retryable=True))
                elif current['state'] == 'cancelling':
                    self.store.transition(job['id'], 'cancelled')
            finally:
                if self.process:
                    if self.process.poll() is None:
                        self._signal(signal.SIGKILL)
                    self.process.wait()
                    if self.process.stdout:
                        self.process.stdout.close()
                    self.process = None

    def _run(self, job: dict[str, Any]) -> None:
        workspace = self.store.directory / 'jobs' / job['id']
        workspace.mkdir(parents=True, exist_ok=True, mode=0o700)
        data = self.prepare(job)
        atomic_json(workspace / 'request.json', data)
        try:
            self.store.transition(job['id'], 'running')
        except BVSError:
            return  # A queued cancellation won the transaction.
        environment = dict(os.environ)
        environment['PYTHONPATH'] = os.pathsep.join(str(p) for p in sys.path if p)
        environment['TOKENIZERS_PARALLELISM'] = 'false'
        environment['OMP_NUM_THREADS'] = '2'
        self.process = subprocess.Popen([sys.executable, '-m', 'bvs.jobs.worker', str(workspace / 'request.json')], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, start_new_session=True, env=environment)
        assert self.process.stdout is not None
        cancellation: float | None = None
        result: dict[str, Any] | None = None
        error: dict[str, Any] | None = None
        while True:
            state = self.store.get(job['id'])['state']
            if state == 'cancelling' or self.stopping.is_set():
                cancellation = cancellation or time.monotonic()
                (workspace / 'cancel').touch()
                elapsed = time.monotonic() - cancellation
                if elapsed > 7:
                    self._signal(signal.SIGKILL)
                elif elapsed > 5:
                    self._signal(signal.SIGTERM)
            readable, _, _ = select.select([self.process.stdout], [], [], .05)
            if readable:
                line = self.process.stdout.readline()
                if line:
                    message = json.loads(line)
                    if message['type'] == 'progress':
                        self.store.progress(job['id'], message['value'])
                    elif message['type'] == 'result':
                        result = message['value']
                    elif message['type'] == 'error':
                        error = message['value']
                elif self.process.poll() is not None:
                    break
            elif self.process.poll() is not None:
                break
        state = self.store.get(job['id'])['state']
        if self.stopping.is_set():
            self.store.transition(job['id'], 'interrupted')
        elif state == 'cancelling':
            self.store.transition(job['id'], 'cancelled')
        elif self.process.returncode == 0 and result is not None:
            self._publish(job['id'], result, workspace)
            self.store.transition(job['id'], 'succeeded', result=result,
                                  progress=dict(phase='complete', completed=1, total=1, unit='steps', message='Complete'))
        elif error:
            self.store.transition(job['id'], 'failed', error=error)
        else:
            self.store.transition(job['id'], 'interrupted')

    def _publish(self, job_id: str, value: Any, workspace: Path) -> None:
        if isinstance(value, dict):
            if 'download_url' in value and 'path' in value:
                path = Path(value['path']).resolve()
                if not path.is_relative_to(workspace.resolve()) or path.suffix == '.part' or not path.is_file():
                    raise BVSError('INVALID_MEDIA', 'Worker produced an invalid artifact')
                self.store.add_artifact(job_id, dict(value))
                value.pop('path')
            for child in value.values():
                self._publish(job_id, child, workspace)
        elif isinstance(value, list):
            for child in value:
                self._publish(job_id, child, workspace)
