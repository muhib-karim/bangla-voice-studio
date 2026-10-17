import io
import time
import wave
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from bvs.config import Settings
from bvs.web.app import create_app


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


def wav_bytes(seconds: int = 3, silent: bool = False) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as stream:
        stream.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        stream.writeframes((b"\0\0" if silent else b"\x10\x10") * (24000 * seconds))
    return buffer.getvalue()


def test_normalization_and_validation_envelope(client: TestClient) -> None:
    response = client.post("/api/v1/normalizations", json={"text": "৳৫০"})
    assert response.status_code == 200
    assert response.json()["text"] == "পঞ্চাশ টাকা"
    error = client.post("/api/v1/normalizations", json={"text": "a", "surprise": True})
    assert error.status_code == 422
    assert error.json()["error"]["details"]
    assert client.get("/api/v1/missing").status_code == 404
    assert client.get("/api/v1/missing").json()["error"]["code"] == "NOT_FOUND"


def test_speech_idempotency_artifact_range_and_privacy(client: TestClient) -> None:
    payload = {"engine_id": "dummy", "text": "কথা", "captions": ["srt", "vtt"]}
    first = client.post("/api/v1/syntheses", json=payload, headers={"Idempotency-Key": "same"})
    assert first.status_code == 202, first.text
    assert first.headers["location"].endswith(first.json()["id"])
    again = client.post("/api/v1/syntheses", json=payload, headers={"Idempotency-Key": "same"})
    assert again.json()["id"] == first.json()["id"]
    different = client.post(
        "/api/v1/syntheses", json={**payload, "text": "অন্য"}, headers={"Idempotency-Key": "same"}
    )
    assert different.status_code == 409
    job = finish(client, first.json()["id"])
    audio = next(a for a in job["result"]["artifacts"] if a["media_type"] == "audio/wav")
    response = client.get(audio["download_url"])
    with wave.open(io.BytesIO(response.content)) as stream:
        assert stream.getframerate() == 24000
        # PLAN §5: 2,400 frames per non-whitespace Unicode codepoint.
        assert stream.getnframes() == 2400 * len("কথা") == 7200
    partial = client.get(audio["download_url"], headers={"Range": "bytes=0-3"})
    assert partial.status_code == 206 and partial.content == b"RIFF"
    assert "text" not in client.get("/api/v1/jobs").json()["items"][0]
    assert "request" not in client.get("/api/v1/jobs").json()["items"][0]
    assert client.get("/api/v1/jobs?limit=101").status_code == 422


def test_upload_transcribe_clone_and_delete_dependencies(client: TestClient) -> None:
    upload = client.post(
        "/api/v1/uploads",
        data={"purpose": "reference"},
        files={"file": ("../../x.wav", wav_bytes(), "audio/wav")},
    )
    assert upload.status_code == 201, upload.text
    assert upload.json()["name"] == "x.wav"
    reference = {"upload_id": upload.json()["id"], "transcript": "আগের কথা"}
    clone = client.post(
        "/api/v1/clones", json={"engine_id": "dummy", "text": "নতুন", "reference": reference}
    )
    assert clone.status_code == 202, clone.text
    finish(client, clone.json()["id"])
    transcription = client.post(
        "/api/v1/uploads",
        data={"purpose": "transcription"},
        files={"file": ("silent.wav", wav_bytes(silent=True), "audio/wav")},
    ).json()
    job = client.post(
        "/api/v1/transcriptions", json={"engine_id": "fake-asr", "upload_id": transcription["id"]}
    ).json()
    result = finish(client, job["id"])["result"]
    assert result["text"] == ""
    assert result["warnings"]
    assert client.delete("/api/v1/uploads/" + transcription["id"]).status_code == 204


def test_book_preview_and_dummy_book(client: TestClient) -> None:
    text = "# সূচনা\n\nকথা।\n\n# শেষ\n\nবিদায়।"
    preview = client.post("/api/v1/audiobooks/previews", json={"text": text})
    assert preview.status_code == 200, preview.text
    assert len(preview.json()["chapters"]) == 2
    response = client.post(
        "/api/v1/audiobooks",
        json={"engine_id": "dummy", "text": text, "title": "বই", "formats": ["wav"]},
    )
    assert response.status_code == 202, response.text
    result = finish(client, response.json()["id"])["result"]
    assert result["type"] == "audiobook" and len(result["chapters"]) == 2
    assert result["chapters"][1]["start_ms"] >= result["chapters"][0]["end_ms"]


def test_engine_metadata_and_preflight(client: TestClient) -> None:
    engines = client.get("/api/v1/engines").json()["items"]
    assert {
        "dummy",
        "mms",
        "indic-parler",
        "indicf5",
        "omnivoice",
        "voxcpm2-bn",
        "fake-asr",
        "faster-whisper",
    } <= {e["id"] for e in engines}
    assert all("factory" not in e for e in engines)
    assert client.get("/api/v1/engines/voxcpm2-bn").json()["availability"] == "planned"
    missing = client.post("/api/v1/syntheses", json={"engine_id": "mms", "text": "কথা"})
    assert missing.status_code == 409
    assert (
        client.post("/api/v1/clones", json={"engine_id": "dummy", "text": "কথা"}).status_code == 422
    )


def test_openapi_lists_plan_routes(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for route in [
        "health",
        "normalizations",
        "engines",
        "engines/{engine_id}",
        "engines/{engine_id}/downloads",
        "uploads",
        "uploads/{upload_id}",
        "syntheses",
        "clones",
        "transcriptions",
        "audiobooks/previews",
        "audiobooks",
        "jobs",
        "jobs/{job_id}",
        "jobs/{job_id}/cancellations",
        "jobs/{job_id}/resumptions",
        "artifacts/{artifact_id}",
    ]:
        assert "/api/v1/" + route in paths
