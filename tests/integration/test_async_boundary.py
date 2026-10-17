"""The HTTP transport must run without an external listening socket."""

import asyncio
from pathlib import Path

import httpx
import pytest

from bvs.config import Settings
from bvs.web.app import create_app


@pytest.mark.asyncio
async def test_inprocess_lifespan_and_normalization(tmp_path: Path) -> None:
    app = create_app(Settings(data_dir=tmp_path, model_cache_dir=tmp_path / "models", demo=True))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://testserver"
        ) as client:
            response = await asyncio.wait_for(
                client.post("/api/v1/normalizations", json={"text": "৳৫০"}), timeout=3
            )
    assert response.status_code == 200
    assert response.json()["text"] == "পঞ্চাশ টাকা"
