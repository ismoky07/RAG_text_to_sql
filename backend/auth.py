"""
Authentification JWT + RBAC
============================
Gestion des tokens JWT, hashing de mots de passe, rôles et dependency FastAPI.
"""

import os
import re
import json
from datetime import datetime, timedelta, timezone

import jwt
import bcrypt
import psycopg2
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

DB_URL_PSYCOPG2 = os.getenv("DATABASE_URL_PSYCOPG2", "postgresql://postgres:postgres@localhost:5433/text_to_sql_db")
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security = HTTPBearer()

ALL_TABLES = ["clients", "produits", "commandes"]


# ── Password hashing ─────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt."""
    pwd_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Vérifie un mot de passe contre son hash."""
    pwd_bytes = password.encode("utf-8")[:72]
    return bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))


# ── Validation ────────────────────────────────────────────────────────────────

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_email(email: str) -> str | None:
    """Valide le format de l'email. Retourne un message d'erreur ou None si valide."""
    if len(email) > 200:
        return "L'email ne doit pas dépasser 200 caractères."
    if not EMAIL_REGEX.match(email):
        return "Format d'email invalide (ex: nom@domaine.com)."
    return None


def validate_password(password: str) -> str | None:
    """Valide la robustesse du mot de passe. Retourne un message d'erreur ou None si valide."""
    if len(password) < 8:
        return "Le mot de passe doit contenir au moins 8 caractères."
    if len(password) > 72:
        return "Le mot de passe ne doit pas dépasser 72 caractères."
    if not re.search(r"[A-Z]", password):
        return "Le mot de passe doit contenir au moins une lettre majuscule."
    if not re.search(r"[a-z]", password):
        return "Le mot de passe doit contenir au moins une lettre minuscule."
    if not re.search(r"\d", password):
        return "Le mot de passe doit contenir au moins un chiffre."
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", password):
        return "Le mot de passe doit contenir au moins un caractère spécial (!@#$%^&*...)."
    return None


def validate_username(username: str) -> str | None:
    """Valide le nom d'utilisateur. Retourne un message d'erreur ou None si valide."""
    if len(username) < 3:
        return "Le nom d'utilisateur doit contenir au moins 3 caractères."
    if len(username) > 50:
        return "Le nom d'utilisateur ne doit pas dépasser 50 caractères."
    if not re.match(r"^[a-zA-Z0-9_àâäéèêëïîôùûüçÀÂÄÉÈÊËÏÎÔÙÛÜÇ -]+$", username):
        return "Le nom d'utilisateur ne peut contenir que des lettres, chiffres, espaces, tirets et underscores."
    return None


# ── JWT Tokens ────────────────────────────────────────────────────────────────

def create_token(user_id: int, email: str, role: str = "user", allowed_tables: list | None = None) -> str:
    """Crée un token JWT avec expiration, rôle et tables autorisées."""
    if allowed_tables is None:
        allowed_tables = ALL_TABLES
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "allowed_tables": allowed_tables,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Décode et valide un token JWT."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expiré.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide.")


# ── FastAPI Dependencies ─────────────────────────────────────────────────────

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency FastAPI : vérifie le token et retourne l'utilisateur avec rôle."""
    payload = decode_token(credentials.credentials)
    role = payload.get("role", "user")
    allowed_tables = payload.get("allowed_tables", ALL_TABLES)
    if role == "admin":
        allowed_tables = ALL_TABLES
    return {
        "user_id": payload["user_id"],
        "email": payload["email"],
        "role": role,
        "allowed_tables": allowed_tables,
    }


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Dependency FastAPI : vérifie que l'utilisateur est admin."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs.",
        )
    return user


# ── User DB helpers ───────────────────────────────────────────────────────────

def get_user_by_email(email: str) -> dict | None:
    """Récupère un utilisateur par email (avec rôle et tables)."""
    try:
        conn = psycopg2.connect(DB_URL_PSYCOPG2)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, email, hashed_password, role, allowed_tables FROM users WHERE email = %s",
            (email,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return {
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "hashed_password": row[3],
                "role": row[4] or "user",
                "allowed_tables": row[5] if row[5] else ALL_TABLES,
            }
        return None
    except Exception:
        return None


def create_user(username: str, email: str, password: str) -> dict:
    """Crée un nouvel utilisateur. Le premier utilisateur devient admin automatiquement."""
    hashed = hash_password(password)
    conn = psycopg2.connect(DB_URL_PSYCOPG2)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    user_count = cur.fetchone()[0]
    role = "admin" if user_count == 0 else "user"
    allowed_tables = ALL_TABLES

    cur.execute(
        "INSERT INTO users (username, email, hashed_password, role, allowed_tables) VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (username, email, hashed, role, json.dumps(allowed_tables)),
    )
    user_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return {
        "id": user_id,
        "username": username,
        "email": email,
        "role": role,
        "allowed_tables": allowed_tables,
    }


def ensure_users_table():
    """Crée la table users si elle n'existe pas et ajoute les colonnes RBAC."""
    try:
        conn = psycopg2.connect(DB_URL_PSYCOPG2)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) NOT NULL,
                email VARCHAR(200) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'user',
                allowed_tables JSONB NOT NULL DEFAULT '["clients", "produits", "commandes"]',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name = 'role'
                ) THEN
                    ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user';
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name = 'allowed_tables'
                ) THEN
                    ALTER TABLE users ADD COLUMN allowed_tables JSONB NOT NULL DEFAULT '["clients", "produits", "commandes"]';
                END IF;
            END $$;
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("[Auth] Table users prête (avec RBAC).")
    except Exception as e:
        print(f"[Auth] Erreur création table users : {e}")
