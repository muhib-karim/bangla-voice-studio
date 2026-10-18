from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from bvs.config import Settings
from bvs.web.app import create_app

BOOK = "# সূচনা\n\nকথা।\n\n# শেষ\n\nবিদায়।"
UNITS = 4  # two chapters, each a spoken title plus one sentence


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(
        create_app(Settings(data_dir=tmp_path, model_cache_dir=tmp_path / "models", demo=True))
    ) as client:
        yield client


def finish(client: TestClient, job_id: str) -> dict[str, Any]:
    for _ in range(200):
        job = client.get(f"/api/v1/jobs/{job_id}").json()
        if job["state"] in {"succeeded", "failed", "cancelled", "interrupted"}:
            assert job["state"] == "succeeded", job
            return dict(job)
        time.sleep(0.05)
    pytest.fail("worker did not finish")


def _render(client: TestClient, **extra: Any) -> dict[str, Any]:
    response = client.post(
        "/api/v1/audiobooks",
        json={"engine_id": "dummy", "text": BOOK, "title": "বই", "formats": ["wav"], **extra},
    )
    assert response.status_code == 202, response.text
    result: dict[str, Any] = finish(client, response.json()["id"])["result"]
    return result


def _timeline(result: dict[str, Any]) -> list[tuple[int, int]]:
    return [(c["start_ms"], c["end_ms"]) for c in result["chapters"]]


def test_identical_book_reuses_every_chunk(client: TestClient) -> None:
    first = _render(client)
    assert first["cache_hits"] == 0
    second = _render(client)
    assert second["cache_hits"] == UNITS
    assert _timeline(second) == _timeline(first)


def test_changed_seed_invalidates_the_cache(client: TestClient) -> None:
    _render(client, seed=1)
    assert _render(client, seed=2)["cache_hits"] == 0


def test_corrupt_chunk_is_rerendered(client: TestClient, tmp_path: Path) -> None:
    first = _render(client)
    entries = sorted(p for p in tmp_path.rglob("chunk-cache/*/*.wav"))
    assert len(entries) == UNITS
    entries[0].write_bytes(b"RIFF")
    again = _render(client)
    assert again["cache_hits"] == UNITS - 1
    assert _timeline(again) == _timeline(first)
    assert len(sorted(tmp_path.rglob("chunk-cache/*/*.wav"))) == UNITS


def test_resumed_book_reuses_chunks_finished_before_it_stopped(tmp_path: Path) -> None:
    app = create_app(Settings(data_dir=tmp_path, model_cache_dir=tmp_path / "models", demo=True))
    # Until the app starts its supervisor a submitted book stays queued, so cancelling it
    # is deterministic.
    idle = TestClient(app)
    response = idle.post(
        "/api/v1/audiobooks",
        json={"engine_id": "dummy", "text": BOOK, "title": "বই", "formats": ["wav"]},
    )
    assert response.status_code == 202, response.text
    stopped = response.json()["id"]
    cancelled = idle.post(f"/api/v1/jobs/{stopped}/cancellations", json={})
    assert cancelled.json()["state"] == "cancelled"

    with TestClient(app) as client:
        first = _render(client)
        entries = sorted(tmp_path.rglob("chunk-cache/*/*.wav"))
        assert len(entries) == UNITS
        for entry in entries[:2]:
            entry.unlink()  # only the other chunks count as finished
        resumed = client.post(f"/api/v1/jobs/{stopped}/resumptions", json={})
        assert resumed.status_code == 202, resumed.text
        job = finish(client, resumed.json()["id"])
        assert job["result"]["cache_hits"] == UNITS - 2
        assert _timeline(job["result"]) == _timeline(first)
        assert len(sorted(tmp_path.rglob("chunk-cache/*/*.wav"))) == UNITS
        again = client.post(f"/api/v1/jobs/{job['id']}/resumptions", json={})
        assert again.status_code == 409, again.text
