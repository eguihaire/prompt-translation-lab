import base64
import io
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import BadRequestError
from openai import OpenAI

if Path('.env').exists():
    load_dotenv()

app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')

MIN_AUDIO_BYTES = 2048


def _looks_like_wav(audio_bytes: bytes) -> bool:
    if len(audio_bytes) < 44:
        return False
    return audio_bytes[:4] == b'RIFF' and audio_bytes[8:12] == b'WAVE'


def _openai_client() -> OpenAI:
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY manquante.')
    return OpenAI(api_key=api_key, base_url=os.getenv('OPENAI_BASE_URL') or None)


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
            return JSONResponse({'text': '', 'skipped': True})

        audio_bytes = base64.b64decode(audio_b64)
        if len(audio_bytes) < MIN_AUDIO_BYTES:
            return JSONResponse({'text': '', 'skipped': True})

        previous_text = data.get('previous_text') or ''
        language = data.get('language') or 'fr'
        mime_type = data.get('mime_type') or 'audio/wav'

        if mime_type == 'audio/wav' and not _looks_like_wav(audio_bytes):
            return JSONResponse({'text': '', 'skipped': True, 'warning': 'Chunk WAV invalide ignoré.'})

        model = os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-transcribe")

        prompt = (
            "This is a live transcription of a French news or journalism audio stream. "
            "Preserve names, acronyms, numbers, places, and punctuation accurately. "
            "Keep formatting clean and readable. "
            + (previous_text[-400:] if previous_text else "")
        )

        filename = 'chunk.wav' if mime_type == 'audio/wav' else 'chunk.webm'

        transcription = _openai_client().audio.transcriptions.create(
            model=model,
            file=(filename, io.BytesIO(audio_bytes), mime_type),
            language=language,
            prompt=prompt,
        )

        text = (getattr(transcription, 'text', '') or '').strip()
        return JSONResponse({'text': text, 'skipped': False})
    except BadRequestError as exc:
        body = getattr(exc, 'body', None)
        error_code = ''
        error_param = ''
        if isinstance(body, dict):
            error_obj = body.get('error') or {}
            error_code = str(error_obj.get('code') or '')
            error_param = str(error_obj.get('param') or '')

        message = str(exc)
        invalid_audio = (
            'Audio file might be corrupted or unsupported' in message
            or error_code == 'invalid_value'
            or error_param == 'file'
        )
        if invalid_audio:
            return JSONResponse(
                {'text': '', 'skipped': True, 'warning': 'Chunk audio ignoré (invalide/silencieux).'},
                status_code=200,
            )
        return JSONResponse({'error': message}, status_code=500)
    except Exception as exc:
        message = str(exc)
        if 'Audio file might be corrupted or unsupported' in message or "'param': 'file'" in message:
            return JSONResponse(
                {'text': '', 'skipped': True, 'warning': 'Chunk audio ignoré (invalide/silencieux).'},
                status_code=200,
            )
        return JSONResponse({'error': message}, status_code=500)
