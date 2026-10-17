from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from bvs.config import Settings
from bvs.errors import BVSError
from bvs.jobs.store import Store
from bvs.service import Service
from bvs.web.schemas import SpeechInput


def test_idempotency_is_atomic_and_payload_checked(tmp_path: Path) -> None:
    store = Store(tmp_path)

    def submit() -> str:
        return str(store.create("speech", {"engine_id": "dummy", "text": "কথা"}, key="one")["id"])

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(lambda _: submit(), range(16)))
    assert len(set(ids)) == 1
    with pytest.raises(BVSError, match="different"):
        store.create("speech", {"text": "different"}, key="one")
    assert len(store.list()) == 1


def test_restart_terminal_immutability_and_tombstone(tmp_path: Path) -> None:
    store = Store(tmp_path)
    job = store.create("speech", {"engine_id": "dummy", "text": "কথা"}, key="intent")
    store.transition(job["id"], "running")
    store.recover()
    assert store.get(job["id"])["state"] == "interrupted"
    with pytest.raises(BVSError):
        store.transition(job["id"], "succeeded")
    store.delete(job["id"])
    with pytest.raises(BVSError) as error:
        store.create("speech", {"engine_id": "dummy", "text": "কথা"}, key="intent")
    assert error.value.code == "IDEMPOTENCY_EXPIRED"


def test_queue_limit_and_queued_cancel(tmp_path: Path) -> None:
    store = Store(tmp_path)
    jobs = [store.create("speech", {"text": str(i)}) for i in range(20)]
    with pytest.raises(BVSError) as error:
        store.create("speech", {"text": "overflow"})
    assert error.value.code == "QUEUE_FULL"
    store.cancel(jobs[0]["id"])
    assert store.get(jobs[0]["id"])["state"] == "cancelled"
    store.cancel(jobs[0]["id"])
    store.create("speech", {"text": "space"})


def test_real_process_job_and_state_directory_lock(tmp_path: Path) -> None:
    service = Service(Settings(data_dir=tmp_path, model_cache_dir=tmp_path / "models", demo=True))
    with service:
        with pytest.raises(BVSError) as error:
            with Service(service.settings):
                pass
        assert error.value.code == "WORKER_LOCKED"
        job = service.submit_job(
            "speech", SpeechInput(engine_id="dummy", text="কথা", captions=["srt", "vtt"])
        )
        result = service.wait(job["id"], timeout=20)
        assert result["state"] == "succeeded", result.get("error")
        assert len(result["result"]["artifacts"]) == 3
        assert all(
            Path(service.artifact(a["id"])["path"]).is_file() for a in result["result"]["artifacts"]
        )


def test_failed_process_and_atomic_part_recovery(tmp_path: Path) -> None:
    store = Store(tmp_path)
    job = store.create("speech", {"engine_id": "dummy", "text": "কথা"})
    directory = tmp_path / "jobs" / job["id"]
    directory.mkdir(parents=True)
    (directory / "bad.wav.part").write_bytes(b"RIFF")
    (directory / "keep.txt").write_text("keep")
    store.transition(job["id"], "running")
    store.recover()
    assert not (directory / "bad.wav.part").exists()
    assert (directory / "keep.txt").exists()
    assert store.get(job["id"])["state"] == "interrupted"
