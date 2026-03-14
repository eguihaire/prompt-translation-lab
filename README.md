# Super Scribe V1 — Transcription live d'un onglet Chrome (ElevenLabs Realtime STT + Vercel)

Cette app FastAPI capture l'audio d'un onglet Chrome côté navigateur, envoie des micro-chunks audio au serveur via WebSocket, puis transcrit en quasi temps réel avec l'API Realtime Speech-to-Text d'ElevenLabs.

## Pourquoi cette architecture

- **Simple** : 1 backend FastAPI + 1 page HTML/JS.
- **Sécurisée** : la clé ElevenLabs reste **uniquement côté serveur**.
- **Faible latence** : envoi fréquent de chunks audio et affichage live.
- **Compatible Vercel** : déploiement serverless Python direct.

## Variables d'environnement

Sur Vercel (Project Settings → Environment Variables) :

- `ELEVENLABS_API_KEY` (**obligatoire**)
- `ELEVENLABS_STT_MODEL_ID` (optionnel, défaut: `scribe_v1`)
- `ELEVENLABS_REALTIME_WS_URL` (optionnel, défaut: `wss://api.elevenlabs.io/v1/speech-to-text/realtime`)

En local, vous pouvez utiliser un `.env`.

## Lancer en local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

Puis ouvrir `http://localhost:8000`.

## Déploiement Vercel

1. Push le repo sur GitHub.
2. Import dans Vercel.
3. Ajouter les variables d'environnement ci-dessus.
4. Deploy.

Vercel utilise `vercel.json` pour router toutes les requêtes vers `app.py`.

## Usage

1. Cliquer **Start**.
2. Dans le sélecteur Chrome, choisir l'onglet à transcrire.
3. **Cocher "Partager l'audio"**.
4. Lire le flux transcrit en direct.

## Limites pratiques

- Chrome impose l'UI native de partage d'écran/onglet.
- Sans audio partagé, aucune transcription ne remonte.
- Le protocole de messages ElevenLabs peut évoluer; adaptez l'extraction de texte si nécessaire.
