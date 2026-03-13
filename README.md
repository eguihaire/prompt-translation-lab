# Mini app — Transcription live d'un onglet Chrome (OpenAI + Vercel)

Cette app FastAPI capture l'audio d'un onglet Chrome côté navigateur, envoie des micro-chunks audio au serveur, puis transcrit en quasi temps réel avec l'API OpenAI.

## Pourquoi cette architecture

- **Simple** : 1 backend FastAPI + 1 page HTML/JS.
- **Robuste** : la clé API OpenAI reste **uniquement côté serveur**.
- **Faible latence** : envoi de chunks audio toutes ~1.2 secondes.
- **Compatible Vercel** : déploiement serverless Python direct.

## Variables d'environnement

Sur Vercel (Project Settings → Environment Variables) :

- `OPENAI_API_KEY` (**obligatoire**)
- `OPENAI_TRANSCRIBE_MODEL` (optionnel, défaut: `gpt-4o-mini-transcribe`)
- `OPENAI_BASE_URL` (optionnel, si proxy/API compatible)

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

1. Cliquer **Démarrer**.
2. Dans le sélecteur Chrome, choisir l'onglet à transcrire.
3. **Cocher "Partager l'audio"**.
4. Lire le flux transcrit en direct.

## Limites pratiques

- Chrome impose l'UI native de partage d'écran/onglet.
- Sans audio partagé, aucune transcription ne remonte.
- Pour encore moins de latence, un pipeline WebSocket/Realtimes peut aller plus loin, mais est plus complexe.


## Publier dans votre repo GitHub `eguihaire/transcription-live`

Depuis ce projet local :

```bash
git remote add origin https://github.com/eguihaire/transcription-live.git
git branch -M main
git push -u origin main
```

Si `origin` existe déjà :

```bash
git remote set-url origin https://github.com/eguihaire/transcription-live.git
git push -u origin main
```

> Remarque: dans certains environnements d'entreprise/proxy, l'accès GitHub peut être bloqué. Dans ce cas, exécutez simplement les commandes ci-dessus depuis votre machine locale.
