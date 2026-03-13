import base64
import io
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI

if Path('.env').exists():
    load_dotenv()

app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')


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
            return JSONResponse({'text': ''})

        audio_bytes = base64.b64decode(audio_b64)
        previous_text = data.get('previous_text') or ''
        language = data.get('language') or 'fr'
        mime_type = data.get('mime_type') or 'audio/webm'

        model = os.getenv('OPENAI_TRANSCRIBE_MODEL', 'gpt-4o-mini-transcribe')
        prompt = previous_text[-240:] if previous_text else ''

        transcription = _openai_client().audio.transcriptions.create(
            model=model,
            file=('chunk.webm', io.BytesIO(audio_bytes), mime_type),
            language=language,
            prompt=prompt,
        )

        text = (getattr(transcription, 'text', '') or '').strip()
        return JSONResponse({'text': text})
    except Exception as exc:
        return JSONResponse({'error': str(exc)}, status_code=500)
