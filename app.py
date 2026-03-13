import base64
import io
import os
import re
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




def _post_process_transcript(text: str, previous_text: str) -> str:
    text = (text or '').strip()
    if not text:
        return ''

    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)

    should_capitalize = not previous_text or previous_text.rstrip().endswith(('.', '!', '?'))
    if should_capitalize:
        for i, ch in enumerate(text):
            if ch.isalpha():
                text = text[:i] + ch.upper() + text[i + 1:]
                break

    return text

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

        rolling_context = previous_text[-400:] if previous_text else ""
        prompt = (
            "Transcription française fidèle, mot à mot. "
            "N'ajoute rien, ne résume pas, ne reformule pas. "
            "Conserve strictement les noms propres, acronymes, nombres, lieux et citations. "
            "Améliore la ponctuation et la casse uniquement, sans changer les mots prononcés. "
            "Assure une bonne continuité entre segments consécutifs; n'invente pas de mots absents de l'audio. "
            "Contexte précédent (verbatim): "
            + rolling_context
        )

        filename = 'chunk.wav' if mime_type == 'audio/wav' else 'chunk.webm'

        transcription = _openai_client().audio.transcriptions.create(
            model=model,
            file=(filename, io.BytesIO(audio_bytes), mime_type),
            language=language,
            prompt=prompt,
        )

        raw_text = (getattr(transcription, 'text', '') or '').strip()
        text = _post_process_transcript(raw_text, previous_text)
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
