import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from dotenv import load_dotenv
from openai import OpenAI

# Charger .env (clé OpenAI stockée dans Codespaces, non commitée)
if Path(".env").exists():
    load_dotenv()

app = FastAPI()

# Servir /static (notre index.html)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def home():
    # Redirige vers l'interface
    return HTMLResponse('<meta http-equiv="refresh" content="0; url=/static/index.html">')

@app.post("/translate")
async def translate(req: Request):
    data = await req.json()
    prompt = (data.get("prompt") or "You are a professional translator. Be faithful, clear, neutral.").strip()
    source = (data.get("source_text") or "").strip()
    if not source:
        return JSONResponse({"translation": "⚠️ Merci d'entrer un texte source."})

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return JSONResponse({"translation": "❌ Clé API manquante (mettre OPENAI_API_KEY dans .env)"} )

    client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL") or None)
    model = os.getenv("OPENAI_MODEL", "gpt-4.1")

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": [{"type": "text", "text": prompt}]},
            {"role": "user",   "content": [{"type": "text", "text": f"Translate to English:\n---\n{source}"}]},
        ],
        temperature=0.2,
    )
    return JSONResponse({"translation": resp.output_text.strip()})
