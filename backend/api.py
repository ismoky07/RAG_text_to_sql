"""
FastAPI Backend - Text-to-SQL Pipeline
=======================================
Expose le workflow via une API REST.

Usage : uvicorn main:app --reload --port 8000
"""

import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents import text_to_sql_workflow, load_knowledge

# ── App FastAPI ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Text-to-SQL API",
    description="Posez une question en langage naturel, obtenez une réponse depuis la base de données.",
    version="1.0.0",
)

# CORS pour autoriser le frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Modèles Pydantic ─────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    question: str
    response: str


# ── Événement de démarrage ────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    """Charge la knowledge base au démarrage du serveur."""
    await load_knowledge()
    print("[API] Knowledge base chargée. Serveur prêt.")


# ── Routes ────────────────────────────────────────────────────────────────────
@app.post("/api/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """Poser une question en langage naturel."""
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="La question ne peut pas être vide.")

    if len(question) > 1000:
        raise HTTPException(status_code=400, detail="La question est trop longue (max 1000 caractères).")

    try:
        run_response = text_to_sql_workflow.run(question)
        response_text = run_response.content or "Désolé, je n'ai pas pu traiter votre question."

        return AskResponse(question=question, response=response_text)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne : {str(e)}")


@app.get("/api/health")
async def health_check():
    """Vérifier que l'API est en ligne."""
    return {"status": "ok"}
