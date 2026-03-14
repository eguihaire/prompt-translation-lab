import base64
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

if Path('.env').exists():
    load_dotenv()

app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')


def _elevenlabs_api_key() -> str:
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        raise RuntimeError('ELEVENLABS_API_KEY manquante.')
    return api_key


def _extract_text(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ''

    for key in ('text', 'transcript'):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    data = payload.get('data')
    if isinstance(data, dict):
        nested = _extract_text(data)
        if nested:
            return nested

    alternatives = payload.get('alternatives')
    if isinstance(alternatives, list):
        for alt in alternatives:
            if isinstance(alt, dict):
                candidate = alt.get('text')
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()

    return ''


@app.get('/', response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse('<meta http-equiv="refresh" content="0; url=/static/index.html">')


@app.get('/health')
def health() -> JSONResponse:
    return JSONResponse({'ok': True})


@app.post('/transcribe-chunk')
async def transcribe_chunk(req: Request) -> JSONResponse:
    try:
        data = await req.json()
        audio_b64 = data.get('audio_b64') or ''
        if not audio_b64:
            return JSONResponse({'text': ''})

        audio_bytes = base64.b64decode(audio_b64)
        mime_type = data.get('mime_type') or 'audio/webm'

        files = {
            'file': ('chunk.webm', audio_bytes, mime_type),
        }
        payload = {
            'model_id': os.getenv('ELEVENLABS_STT_MODEL_ID', 'scribe_v1'),
            'language_code': 'fr',
            'tag_audio_events': 'false',
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                os.getenv('ELEVENLABS_STT_URL', 'https://api.elevenlabs.io/v1/speech-to-text'),
                headers={'xi-api-key': _elevenlabs_api_key()},
                data=payload,
                files=files,
            )

        if resp.status_code >= 400:
            return JSONResponse({'error': resp.text}, status_code=resp.status_code)

        result = resp.json() if resp.content else {}
        text = _extract_text(result)
        return JSONResponse({'text': text})
    except Exception as exc:
        return JSONResponse({'error': str(exc)}, status_code=500)
