"""Command line access to the local narration service."""
from __future__ import annotations

import json
import shutil
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import ValidationError

from bvs.config import Settings
from bvs.download import engine_view
from bvs.errors import BVSError
from bvs.normalise import normalise_with_report
from bvs.registry import list_engines
from bvs.service import Service
from bvs.web.schemas import AudiobookInput, CloneInput, Reference, SpeechInput, TranscribeInput

app = typer.Typer(no_args_is_help=True, help='Local Bangla text, speech and transcription jobs.')
engines = typer.Typer(no_args_is_help=True)
app.add_typer(engines, name='engines')
Output = Annotated[Path, typer.Option('--output', '-o')]
EngineOption = Annotated[str, typer.Option('--engine')]


@contextmanager
def errors() -> Iterator[None]:
    try:
        yield
    except BVSError as exc:
        typer.echo(f'{exc.code}: {exc.message}', err=True)
        code = 3 if exc.code in {'EXTRA_MISSING', 'MODEL_MISSING', 'MODEL_INCOMPLETE', 'ENGINE_UNAVAILABLE', 'OFFLINE', 'WORKER_LOCKED'} else 2
        raise typer.Exit(code) from None
    except (ValidationError, OSError, UnicodeError) as exc:
        typer.echo('Invalid input or inaccessible file: '+type(exc).__name__, err=True)
        raise typer.Exit(2) from None


def check_outputs(paths: list[Path], overwrite: bool) -> None:
    if not overwrite and any(p.exists() for p in paths):
        raise BVSError('INVALID_INPUT', 'Output already exists; use --overwrite to replace it')


def wait(svc: Service, job: dict[str, Any]) -> dict[str, Any]:
    typer.echo('Job '+job['id'], err=True)
    try:
        result = svc.wait(job['id'])
    except KeyboardInterrupt:
        svc.cancel_job(job['id'])
        typer.echo('Cancelled; job ID: '+job['id'], err=True)
        raise typer.Exit(130) from None
    if result['state'] != 'succeeded':
        typer.echo((result.get('error') or {}).get('message', result['state']), err=True)
        raise typer.Exit(130 if result['state'] == 'cancelled' else 4)
    value: dict[str, Any] = result['result']
    return value


def reference_input(svc: Service, path: Path | None, transcript: str | None) -> Reference | None:
    if path is None:
        if transcript:
            raise BVSError('INVALID_INPUT', '--reference-text requires --reference')
        return None
    if not transcript or not transcript.strip():
        raise BVSError('INVALID_INPUT', '--reference-text is required with --reference')
    with path.open('rb') as stream:
        upload = svc.upload(stream, path.name, 'reference')
    return Reference(upload_id=upload['id'], transcript=transcript)


@app.command()
def normalize(text: Annotated[str | None, typer.Argument()] = None, json_output: Annotated[bool, typer.Option('--json')] = False) -> None:
    with errors():
        result = normalise_with_report(text if text is not None else sys.stdin.read())
        typer.echo(json.dumps(asdict(result), ensure_ascii=False) if json_output else result.text)
        for warning in result.warnings:
            typer.echo(warning, err=True)


@engines.command('list')
def engine_list(json_output: Annotated[bool, typer.Option('--json')] = False) -> None:
    with errors():
        settings = Settings()
        values = [engine_view(s, settings.model_cache_dir, offline=settings.offline) for s in list_engines()]
        if json_output:
            typer.echo(json.dumps(values, ensure_ascii=False))
        else:
            for value in values:
                typer.echo(f'{value["id"]}: {value["availability"]}; {value["license"]["identifier"]}; {value["license"]["commercial_use"]}')


def speech(text: str, engine: str, output: Path, normalize: bool, description: str | None, reference: Path | None,
           reference_text: str | None, seed: int, srt: bool, vtt: bool, overwrite: bool, *, clone: bool) -> None:
    with errors():
        formats = [fmt for fmt, enabled in [('srt', srt), ('vtt', vtt)] if enabled]
        if output.suffix.lower() != '.wav':
            raise BVSError('INVALID_INPUT', 'Use a .wav output; encoded exports are deferred to M3')
        check_outputs([output, *(output.with_suffix('.'+f) for f in formats)], overwrite)
        with Service(Settings(demo=engine == 'dummy')) as svc:
            ref = reference_input(svc, reference, reference_text)
            data = dict(engine_id=engine, text=text, normalize=normalize, voice_description=description, reference=ref, seed=seed, captions=formats)
            payload = CloneInput.model_validate(data) if clone else SpeechInput.model_validate(data)
            result = wait(svc, svc.submit_job('clone' if clone else 'speech', payload))
            output.parent.mkdir(parents=True, exist_ok=True)
            for item in result['artifacts']:
                source = Path(svc.artifact(item['id'])['path'])
                shutil.copyfile(source, output.with_suffix(source.suffix))


@app.command()
def say(text: str, engine: EngineOption = 'mms', output: Output = Path('speech.wav'),
        normalize: bool = True, description: str | None = None, reference: Path | None = None,
        reference_text: str | None = None, seed: int = 0, srt: bool = False, vtt: bool = False, overwrite: bool = False) -> None:
    speech(text, engine, output, normalize, description, reference, reference_text, seed, srt, vtt, overwrite, clone=False)


@app.command()
def clone(text: str, engine: EngineOption = 'indicf5', output: Output = Path('clone.wav'),
          reference: Path | None = None, reference_text: str | None = None, normalize: bool = True,
          description: str | None = None, seed: int = 0, srt: bool = False, vtt: bool = False, overwrite: bool = False) -> None:
    speech(text, engine, output, normalize, description, reference, reference_text, seed, srt, vtt, overwrite, clone=True)


@app.command()
def transcribe(input: Path, engine: EngineOption = 'faster-whisper', language: str = 'bn', srt: bool = False,
               vtt: bool = False, word_timestamps: bool = True, output_dir: Path = Path('.'),
               json_output: Annotated[bool, typer.Option('--json')] = False, overwrite: bool = False) -> None:
    with errors():
        captions = [f for f, enabled in [('srt', srt), ('vtt', vtt)] if enabled]
        check_outputs([output_dir / (input.stem+'.'+f) for f in captions], overwrite)
        with Service(Settings(demo=engine == 'fake-asr')) as svc:
            with input.open('rb') as stream:
                upload = svc.upload(stream, input.name, 'transcription')
            payload = TranscribeInput.model_validate(dict(engine_id=engine, upload_id=upload['id'], language=None if language == 'auto' else language, word_timestamps=word_timestamps, captions=captions))
            result = wait(svc, svc.submit_job('transcription', payload))
            typer.echo(json.dumps(result, ensure_ascii=False) if json_output else result['text'])
            output_dir.mkdir(parents=True, exist_ok=True)
            for item in result['artifacts']:
                suffix = Path(item['name']).suffix
                if suffix.lstrip('.') in captions:
                    shutil.copyfile(svc.artifact(item['id'])['path'], output_dir / (input.stem+suffix))


@app.command()
def audiobook(input: Annotated[Path | None, typer.Argument()] = None, text: str | None = None, title: str = 'অডিওবই',
              author: str = '', engine: EngineOption = 'mms', output_dir: Path = Path('book-output'), formats: str = 'wav',
              max_chars: int = 300, chapter_pause_ms: int = 750, reference: Path | None = None, reference_text: str | None = None,
              description: str | None = None, seed: int = 0, normalize: bool = True, srt: bool = False, vtt: bool = False,
              resume: str | None = None, overwrite: bool = False) -> None:
    with errors():
        if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
            raise BVSError('INVALID_INPUT', 'Output directory is not empty; use --overwrite')
        with Service(Settings(demo=engine == 'dummy')) as svc:
            if resume:
                job = svc.resume_audiobook(resume)
            else:
                source = text if text is not None else input.read_text(encoding='utf-8-sig') if input else sys.stdin.read()
                payload = AudiobookInput.model_validate(dict(engine_id=engine, text=source, title=title, author=author, max_chars=max_chars, chapter_pause_ms=chapter_pause_ms, reference=reference_input(svc, reference, reference_text), voice_description=description, seed=seed, normalize=normalize, formats=formats.split(','), captions=[f for f, enabled in [('srt',srt),('vtt',vtt)] if enabled]))
                job = svc.submit_job('audiobook', payload)
            result = wait(svc, job)
            output_dir.mkdir(parents=True, exist_ok=True)
            for item in [*result['artifacts'], *(a for c in result['chapters'] for a in c['artifacts'])]:
                shutil.copyfile(svc.artifact(item['id'])['path'], output_dir / item['name'])


@app.command()
@engines.command('download')
def download(engine: str, model_cache: Path | None = None) -> None:
    with errors():
        settings = Settings(model_cache_dir=model_cache) if model_cache else Settings()
        with Service(settings) as svc:
            result = wait(svc, svc.download(engine))
            typer.echo(json.dumps(result, ensure_ascii=False))


@app.command()
def serve(host: str = '127.0.0.1', port: int = 8000, demo: bool = False) -> None:
    with errors():
        settings = Settings(host=host, port=port, demo=demo)
        import uvicorn
        from bvs.web.app import create_app
        uvicorn.run(create_app(settings), host=host, port=port, workers=1, access_log=False)
