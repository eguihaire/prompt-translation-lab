# Super Scribe V1 — Transcription live d'un onglet Chrome (ElevenLabs STT + Vercel)

Cette app FastAPI capture l'audio d'un onglet Chrome côté navigateur, envoie des micro-chunks audio au backend, puis transcrit en quasi temps réel avec l'API Speech-to-Text d'ElevenLabs.

## Variables d'environnement

- `ELEVENLABS_API_KEY` (**obligatoire**)
- `ELEVENLABS_STT_MODEL_ID` (optionnel, défaut: `scribe_v1`)
- `ELEVENLABS_STT_URL` (optionnel, défaut: `https://api.elevenlabs.io/v1/speech-to-text`)

## Lancer en local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

Puis ouvrir `http://localhost:8000`.
