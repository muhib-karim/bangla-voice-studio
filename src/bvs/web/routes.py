"""Version-one routes using the same service as the CLI."""
from __future__ import annotations

import base64
from dataclasses import asdict
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from bvs.download import engine_view
from bvs.errors import BVSError
from bvs.jobs.store import TERMINAL
from bvs.normalise import NORMALISER_VERSION, normalise_with_report
from bvs.registry import get_spec, list_engines
from bvs.service import Service, public
from bvs.web.schemas import AudiobookInput, BookPreviewInput, CloneInput, EmptyInput, JobKind, JobState, NormaliseInput, SpeechInput, TranscribeInput

router = APIRouter(prefix='/api/v1')


def service(request: Request) -> Service:
    value: Service = request.app.state.service
    return value


Svc = Annotated[Service, Depends(service)]
Key = Annotated[str | None, Header(alias='Idempotency-Key')]
Limit = Annotated[int, Query(ge=1, le=100)]


def accepted(job: dict[str, Any]) -> JSONResponse:
    url = '/api/v1/jobs/'+job['id']
    return JSONResponse(dict(id=job['id'], kind=job['kind'], state=job['state'], status_url=url), status_code=200 if job['state'] in TERMINAL else 202, headers={'Location':url})


def page(rows: list[dict[str, Any]], cursor: str | None, limit: int) -> dict[str, Any]:
    start = 0
    if cursor:
        try:
            last = base64.urlsafe_b64decode(cursor.encode()).decode()
            start = next(i+1 for i, row in enumerate(rows) if row['id'] == last)
        except (ValueError, UnicodeError, StopIteration) as exc:
            raise BVSError('INVALID_INPUT', 'Invalid pagination cursor') from exc
    items = rows[start:start+limit]
    next_cursor = base64.urlsafe_b64encode(items[-1]['id'].encode()).decode() if start+limit < len(rows) else None
    return dict(items=items, next_cursor=next_cursor)


@router.post('/normalizations')
def normalize(payload: NormaliseInput) -> dict[str, Any]:
    return dict(**asdict(normalise_with_report(payload.text)), normaliser_version=NORMALISER_VERSION)


@router.get('/engines')
def engines(svc: Svc, kind: Literal['tts', 'asr'] | None = None, cursor: str | None = None, limit: Limit = 20) -> dict[str, Any]:
    return page([engine_view(s, svc.settings.model_cache_dir, offline=svc.settings.offline) for s in list_engines(kind=kind) if svc.settings.demo or s.maturity != 'test-only'], cursor, limit)


@router.get('/engines/{engine_id}')
def engine(engine_id: str, svc: Svc) -> dict[str, Any]:
    return engine_view(get_spec(engine_id), svc.settings.model_cache_dir, offline=svc.settings.offline)


@router.post('/engines/{engine_id}/downloads')
def download(engine_id: str, payload: EmptyInput, svc: Svc, key: Key = None) -> JSONResponse:
    return accepted(svc.download(engine_id, key))


@router.post('/uploads', status_code=201)
async def upload(svc: Svc, file: Annotated[UploadFile, File()], purpose: Annotated[Literal['reference', 'transcription', 'book'], Form()]) -> dict[str, Any]:
    try:
        return await run_in_threadpool(svc.upload, file.file, file.filename or 'upload', purpose)
    finally:
        await file.close()


@router.delete('/uploads/{upload_id}', status_code=204)
def delete_upload(upload_id: UUID, svc: Svc) -> Response:
    svc.delete_upload(str(upload_id))
    return Response(status_code=204)


@router.post('/syntheses')
def syntheses(payload: SpeechInput, svc: Svc, key: Key = None) -> JSONResponse:
    return accepted(svc.submit_job('speech', payload, idempotency_key=key))


@router.post('/clones')
def clones(payload: CloneInput, svc: Svc, key: Key = None) -> JSONResponse:
    return accepted(svc.submit_job('clone', payload, idempotency_key=key))


@router.post('/transcriptions')
def transcriptions(payload: TranscribeInput, svc: Svc, key: Key = None) -> JSONResponse:
    return accepted(svc.submit_job('transcription', payload, idempotency_key=key))


@router.post('/audiobooks/previews')
def preview(payload: BookPreviewInput, svc: Svc) -> dict[str, Any]:
    return svc.book_preview(payload)


@router.post('/audiobooks')
def audiobooks(payload: AudiobookInput, svc: Svc, key: Key = None) -> JSONResponse:
    return accepted(svc.submit_job('audiobook', payload, idempotency_key=key))


@router.get('/jobs')
def jobs(svc: Svc, state: JobState | None = None, kind: JobKind | None = None, cursor: str | None = None, limit: Limit = 20) -> dict[str, Any]:
    return page([public(j) for j in svc.store.list(state=state, kind=kind)], cursor, limit)


@router.get('/jobs/{job_id}')
def job(job_id: UUID, svc: Svc) -> dict[str, Any]:
    return svc.get_job(str(job_id))


@router.post('/jobs/{job_id}/cancellations')
def cancel(job_id: UUID, payload: EmptyInput, svc: Svc) -> dict[str, Any]:
    return svc.cancel_job(str(job_id))


@router.post('/jobs/{job_id}/resumptions')
def resume(job_id: UUID, payload: EmptyInput, svc: Svc, key: Key = None) -> JSONResponse:
    return accepted(svc.resume_audiobook(str(job_id), idempotency_key=key))


@router.delete('/jobs/{job_id}', status_code=204)
def delete_job(job_id: UUID, svc: Svc) -> Response:
    svc.store.delete(str(job_id))
    return Response(status_code=204)


@router.get('/artifacts/{artifact_id}')
def artifact(artifact_id: UUID, svc: Svc) -> FileResponse:
    value = svc.artifact(str(artifact_id))
    return FileResponse(value['path'], filename=value['name'], media_type=value['media_type'])
