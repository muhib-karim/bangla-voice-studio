"""Packaged pages and assets must work without a CDN or a frontend build."""

from pathlib import Path

from fastapi.testclient import TestClient

from bvs.config import Settings
from bvs.web.app import create_app


def test_shell_and_local_assets(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, model_cache_dir=tmp_path / "models", demo=True)
    with TestClient(create_app(settings)) as client:
        for route in ("/", "/speak", "/clone", "/transcribe", "/audiobook", "/engines"):
            response = client.get(route)
            assert response.status_code == 200
            assert '<html lang="bn"' in response.text
            assert "/static/app.js" in response.text
            assert client.cookies.get("bvs_csrf")
        for asset in (
            "app.js",
            "styles.css",
            "api.js",
            "jobs.js",
            "i18n.js",
            "fonts/NotoSansBengali.ttf",
            "fonts/OFL.txt",
        ):
            response = client.get("/static/" + asset)
            assert response.status_code == 200, asset
            assert response.content
        assert client.get("/static/fonts/OFL.txt").text.startswith("Copyright")
        assert client.get("/static/../../../pyproject.toml").status_code == 404
