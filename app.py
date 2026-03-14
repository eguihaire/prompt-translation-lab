import asyncio
import json
import os
from pathlib import Path

import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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


def _elevenlabs_ws_url(language: str = 'fr') -> str:
    base = os.getenv(
        'ELEVENLABS_REALTIME_WS_URL',
        'wss://api.elevenlabs.io/v1/speech-to-text/realtime',
    )
    model_id = os.getenv('ELEVENLABS_STT_MODEL_ID', 'scribe_v1')
    return f'{base}?model_id={model_id}&language_code={language}'


def _extract_text(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ''

    if isinstance(payload.get('text'), str):
        return payload['text'].strip()

    for key in ('transcript', 'partial_transcript', 'final_transcript'):
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
            if isinstance(alt, dict) and isinstance(alt.get('text'), str) and alt['text'].strip():
                return alt['text'].strip()

    return ''


@app.get('/', response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse('<meta http-equiv="refresh" content="0; url=/static/index.html">')


@app.get('/health')
def health() -> JSONResponse:
    return JSONResponse({'ok': True})


@app.websocket('/ws/transcribe')
async def ws_transcribe(client_ws: WebSocket) -> None:
    await client_ws.accept()

    language = 'fr'
    key = _elevenlabs_api_key()
    url = _elevenlabs_ws_url(language=language)

    async with websockets.connect(
        url,
        additional_headers={'xi-api-key': key},
        ping_interval=20,
        ping_timeout=20,
        max_size=None,
    ) as eleven_ws:
        await eleven_ws.send(
            json.dumps(
                {
                    'type': 'session_start',
                    'language_code': language,
                    'enable_partials': True,
                }
            )
        )

        async def relay_client_to_eleven() -> None:
            while True:
                message = await client_ws.receive_text()
                payload = json.loads(message)
                event_type = payload.get('type')

                if event_type == 'audio_chunk':
                    audio_b64 = payload.get('audio_b64') or ''
                    if audio_b64:
                        await eleven_ws.send(
                            json.dumps({'type': 'audio_chunk', 'audio_base64': audio_b64})
                        )
                elif event_type == 'stop':
                    await eleven_ws.send(json.dumps({'type': 'stop'}))
                    break

        async def relay_eleven_to_client() -> None:
            while True:
                raw = await eleven_ws.recv()
                if isinstance(raw, bytes):
                    continue

                payload = json.loads(raw)
                text = _extract_text(payload)
                if text:
                    await client_ws.send_json({'text': text})

        try:
            await asyncio.gather(relay_client_to_eleven(), relay_eleven_to_client())
        except WebSocketDisconnect:
            await eleven_ws.close()
        except Exception as exc:
            await client_ws.send_json({'error': str(exc)})
