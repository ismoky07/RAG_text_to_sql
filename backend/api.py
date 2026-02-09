"""
FastAPI Backend - Text-to-SQL Pipeline
=======================================
Expose le workflow via une API REST avec authentification JWT et RBAC.

Usage : uvicorn api:app --reload --port 8000
"""

import os
import json
import uuid
from datetime import datetime

import psycopg2
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agno.exceptions import InputCheckError

from agents import load_knowledge, run_pipeline
from guardrails import (
    is_greeting, is_off_topic, is_destructive, is_prompt_injection,
    GREETING_RESPONSE, OFF_TOPIC_RESPONSE, DESTRUCTIVE_RESPONSE, PROMPT_INJECTION_RESPONSE,
)
from auth import (
    get_current_user, require_admin, create_token, verify_password,
    get_user_by_email, create_user, ensure_users_table,
    validate_email, validate_password, validate_username,
)

DB_URL_PSYCOPG2 = os.getenv("DATABASE_URL_PSYCOPG2", "postgresql://postgres:postgres@localhost:5433/text_to_sql_db")

# ── App FastAPI ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Text-to-SQL API",
    description="Posez une question en langage naturel, obtenez une réponse depuis la base de données.",
    version="1.0.0",
)

# CORS pour autoriser le frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Modèles Pydantic ─────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


class AskRequest(BaseModel):
    question: str
    session_id: str | None = None


class AskResponse(BaseModel):
    question: str
    response: str
    session_id: str
    sql_query: str | None = None


class HistoryItem(BaseModel):
    id: int
    session_id: str
    question: str
    response: str
    created_at: datetime


class UserInfo(BaseModel):
    id: int
    username: str
    email: str
    role: str
    allowed_tables: list[str]
    created_at: datetime


class UpdateUserRoleRequest(BaseModel):
    role: str


class UpdateUserTablesRequest(BaseModel):
    allowed_tables: list[str]


VALID_TABLES = {"clients", "produits", "commandes"}


# ── Historique : sauvegarde en base ───────────────────────────────────────────
def save_to_history(session_id: str, question: str, response: str, user_id: int | None = None):
    """Sauvegarde une question/réponse dans l'historique."""
    try:
        conn = psycopg2.connect(DB_URL_PSYCOPG2)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO conversation_history (session_id, question, response, user_id) VALUES (%s, %s, %s, %s)",
            (session_id, question, response, user_id),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[History] Erreur sauvegarde : {e}")


def ensure_history_table():
    """Crée la table conversation_history si elle n'existe pas."""
    try:
        conn = psycopg2.connect(DB_URL_PSYCOPG2)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(100) NOT NULL,
                user_id INTEGER,
                question TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_history_session ON conversation_history(session_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_history_date ON conversation_history(created_at DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_history_user ON conversation_history(user_id)")
        conn.commit()
        cur.close()
        conn.close()
        print("[History] Table conversation_history prête.")
    except Exception as e:
        print(f"[History] Erreur création table : {e}")


# ── Événement de démarrage ────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    """Charge la knowledge base et initialise les tables au démarrage."""
    ensure_users_table()
    ensure_history_table()
    await load_knowledge()
    print("[API] Knowledge base chargée. Serveur prêt.")


# ── Routes Auth ───────────────────────────────────────────────────────────────
@app.post("/api/auth/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """Créer un nouveau compte utilisateur."""
    if not request.username.strip() or not request.email.strip() or not request.password.strip():
        raise HTTPException(status_code=400, detail="Tous les champs sont obligatoires.")

    username_error = validate_username(request.username.strip())
    if username_error:
        raise HTTPException(status_code=400, detail=username_error)

    email_error = validate_email(request.email.strip())
    if email_error:
        raise HTTPException(status_code=400, detail=email_error)

    password_error = validate_password(request.password)
    if password_error:
        raise HTTPException(status_code=400, detail=password_error)

    existing = get_user_by_email(request.email.strip())
    if existing:
        raise HTTPException(status_code=409, detail="Un compte avec cet email existe déjà.")

    try:
        user = create_user(request.username.strip(), request.email.strip().lower(), request.password)
        token = create_token(user["id"], user["email"], user["role"], user["allowed_tables"])
        return AuthResponse(
            token=token,
            user={
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "role": user["role"],
                "allowed_tables": user["allowed_tables"],
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'inscription : {str(e)}")


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Se connecter avec email et mot de passe."""
    if not request.email.strip() or not request.password.strip():
        raise HTTPException(status_code=400, detail="Email et mot de passe obligatoires.")

    user = get_user_by_email(request.email.strip().lower())
    if not user:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    if not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    token = create_token(user["id"], user["email"], user["role"], user["allowed_tables"])
    return AuthResponse(
        token=token,
        user={
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "allowed_tables": user["allowed_tables"],
        },
    )


@app.get("/api/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Récupérer les informations de l'utilisateur connecté (avec rôle)."""
    return user


# ── Routes protégées ──────────────────────────────────────────────────────────
@app.post("/api/ask", response_model=AskResponse)
async def ask_question(request: AskRequest, user: dict = Depends(get_current_user)):
    """Poser une question en langage naturel."""
    question = request.question.strip()
    session_id = request.session_id or str(uuid.uuid4())

    if not question:
        raise HTTPException(status_code=400, detail="La question ne peut pas être vide.")

    if len(question) > 1000:
        raise HTTPException(status_code=400, detail="La question est trop longue (max 1000 caractères).")

    if is_greeting(question):
        return AskResponse(question=question, response=GREETING_RESPONSE, session_id=session_id)

    if is_off_topic(question):
        return AskResponse(question=question, response=OFF_TOPIC_RESPONSE, session_id=session_id)

    if is_destructive(question):
        return AskResponse(question=question, response=DESTRUCTIVE_RESPONSE, session_id=session_id)

    if is_prompt_injection(question):
        return AskResponse(question=question, response=PROMPT_INJECTION_RESPONSE, session_id=session_id)

    allowed_tables = user.get("allowed_tables", ["clients", "produits", "commandes"])

    try:
        result = run_pipeline(question, session_id=session_id, allowed_tables=allowed_tables)
        response_text = result["response"]
        sql_query = result.get("sql_query")

        save_to_history(session_id, question, response_text, user_id=user["user_id"])

        return AskResponse(question=question, response=response_text, session_id=session_id, sql_query=sql_query)

    except InputCheckError as e:
        return AskResponse(question=question, response=f"Question refusée : {str(e)}", session_id=session_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne : {str(e)}")


@app.get("/api/history", response_model=list[HistoryItem])
async def get_history(user: dict = Depends(get_current_user), limit: int = Query(default=50, le=200)):
    """Récupérer l'historique des conversations de l'utilisateur."""
    try:
        conn = psycopg2.connect(DB_URL_PSYCOPG2)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, session_id, question, response, created_at FROM conversation_history WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
            (user["user_id"], limit),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            HistoryItem(id=r[0], session_id=r[1], question=r[2], response=r[3], created_at=r[4])
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur historique : {str(e)}")


@app.delete("/api/history")
async def clear_history(user: dict = Depends(get_current_user)):
    """Supprimer l'historique de l'utilisateur connecté."""
    try:
        conn = psycopg2.connect(DB_URL_PSYCOPG2)
        cur = conn.cursor()
        cur.execute("DELETE FROM conversation_history WHERE user_id = %s", (user["user_id"],))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Historique supprimé."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur suppression : {str(e)}")


@app.get("/api/health")
async def health_check():
    """Vérifier que l'API est en ligne."""
    return {"status": "ok"}


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES ADMIN
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/admin/users", response_model=list[UserInfo])
async def admin_list_users(admin: dict = Depends(require_admin)):
    """[Admin] Liste tous les utilisateurs avec leurs rôles et permissions."""
    try:
        conn = psycopg2.connect(DB_URL_PSYCOPG2)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, email, role, allowed_tables, created_at FROM users ORDER BY id"
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            UserInfo(
                id=r[0],
                username=r[1],
                email=r[2],
                role=r[3] or "user",
                allowed_tables=r[4] if r[4] else ["clients", "produits", "commandes"],
                created_at=r[5],
            )
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur admin : {str(e)}")


@app.put("/api/admin/users/{user_id}/role")
async def admin_update_role(user_id: int, request: UpdateUserRoleRequest, admin: dict = Depends(require_admin)):
    """[Admin] Modifier le rôle d'un utilisateur."""
    if request.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Rôle invalide. Valeurs : 'admin' ou 'user'.")

    if user_id == admin["user_id"] and request.role != "admin":
        raise HTTPException(status_code=400, detail="Impossible de retirer votre propre rôle admin.")

    try:
        conn = psycopg2.connect(DB_URL_PSYCOPG2)
        cur = conn.cursor()
        cur.execute("UPDATE users SET role = %s WHERE id = %s RETURNING id", (request.role, user_id))
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if not result:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")
        return {"message": f"Rôle mis à jour : {request.role}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur mise à jour rôle : {str(e)}")


@app.put("/api/admin/users/{user_id}/tables")
async def admin_update_tables(user_id: int, request: UpdateUserTablesRequest, admin: dict = Depends(require_admin)):
    """[Admin] Modifier les tables autorisées pour un utilisateur."""
    invalid = set(request.allowed_tables) - VALID_TABLES
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Tables invalides : {invalid}. Tables valides : {VALID_TABLES}",
        )

    if not request.allowed_tables:
        raise HTTPException(status_code=400, detail="Au moins une table doit être autorisée.")

    try:
        conn = psycopg2.connect(DB_URL_PSYCOPG2)
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET allowed_tables = %s WHERE id = %s RETURNING id",
            (json.dumps(request.allowed_tables), user_id),
        )
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if not result:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")
        return {"message": f"Tables autorisées mises à jour : {request.allowed_tables}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur mise à jour tables : {str(e)}")
