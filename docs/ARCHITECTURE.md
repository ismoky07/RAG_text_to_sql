# Architecture technique détaillée

> Documentation complète fichier par fichier du projet AI Data Assistant.
> Pour le guide de démarrage rapide, voir le [README](../README.md).

---

## Table des matières

1. [Backend — `api.py`](#backendapipy)
2. [Backend — `agents.py`](#backendagentspy)
3. [Backend — `auth.py`](#backendauthpy)
4. [Backend — `guardrails.py`](#backendguardrailspy)
5. [Backend — `tools.py`](#backendtoolspy)
6. [Backend — `requirements.txt`](#backendrequirementstxt)
7. [Backend — `Dockerfile`](#backenddockerfile)
8. [Frontend — `main.tsx`](#frontendsrcmaintsx)
9. [Frontend — `index.css`](#frontendsrcindexcss)
10. [Frontend — `App.tsx`](#frontendsrcapptsx)
11. [Frontend — `App.css`](#frontendsrcappcss)
12. [Frontend — `package.json`](#frontendpackagejson)
13. [Frontend — `Dockerfile`](#frontenddockerfile)
14. [Frontend — `nginx.conf`](#frontendnginxconf)
15. [Base de données — `init.sql`](#dbinitsql)
16. [Knowledge — `schema_docs.md`](#knowledgeschema_docsmd)
17. [Conteneurisation — `docker-compose.yml`](#docker-composeyml)

---

## `backend/api.py`

**Point d'entrée de l'API REST FastAPI.**

### Imports

```python
import os, json, uuid
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
```

### Rôle

Expose toute l'application via une API REST. Contient :

- **App FastAPI** avec CORS configuré pour `localhost:3000`, `localhost:5173`, `localhost`
- **Modèles Pydantic** : `RegisterRequest`, `LoginRequest`, `AuthResponse`, `AskRequest`, `AskResponse`, `HistoryItem`, `UserInfo`, `UpdateUserRoleRequest`, `UpdateUserTablesRequest`
- **Startup** (`@app.on_event("startup")`) : appelle `ensure_users_table()`, `ensure_history_table()`, puis `await load_knowledge()` pour charger la knowledge base RAG

### Routes

| Méthode | Route | Protection | Description |
|---|---|---|---|
| `POST` | `/api/auth/register` | — | Inscription avec validation (username, email, password) puis création du JWT |
| `POST` | `/api/auth/login` | — | Connexion email/password, vérification bcrypt, retour JWT |
| `GET` | `/api/auth/me` | JWT | Info utilisateur courant |
| `POST` | `/api/ask` | JWT | Passe par les guardrails, appelle `run_pipeline(question, session_id, allowed_tables)`, sauvegarde dans l'historique |
| `GET` | `/api/history` | JWT | Historique des conversations de l'utilisateur |
| `DELETE` | `/api/history` | JWT | Supprime l'historique de l'utilisateur |
| `GET` | `/api/admin/users` | Admin | Liste tous les utilisateurs avec rôles et tables autorisées |
| `PUT` | `/api/admin/users/{id}/role` | Admin | Change le rôle (admin/user), empêche l'auto-démotion |
| `PUT` | `/api/admin/users/{id}/tables` | Admin | Change les tables autorisées, valide contre `VALID_TABLES = {"clients", "produits", "commandes"}` |
| `GET` | `/api/health` | — | Retourne `{"status": "ok"}` |

### Fonctions utilitaires

- `save_to_history(session_id, question, response, user_id)` — INSERT dans `conversation_history`
- `ensure_history_table()` — CREATE TABLE IF NOT EXISTS + index sur session_id, created_at, user_id

---

## `backend/agents.py`

**Cœur du système — Pipeline Text-to-SQL en 6 étapes (Agno Workflow).**

### Imports

```python
import os, re
from pathlib import Path
from dotenv import load_dotenv

from agno.agent import Agent
from agno.models.mistral import MistralChat
from agno.workflow.step import Step, StepInput, StepOutput
from agno.workflow.workflow import Workflow
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType
from agno.knowledge.embedder.sentence_transformer import SentenceTransformerEmbedder
from agno.knowledge.reader.markdown_reader import MarkdownReader
from agno.knowledge.chunking.semantic import SemanticChunking
from agno.db.postgres import PostgresDb

from tools import execute_sql_readonly
from guardrails import TopicGuardrail, SQLInjectionGuardrail, PromptInjectionGuardrail, OutputSafetyGuardrail
```

### Configuration

| Variable | Rôle |
|---|---|
| `get_model()` | Retourne `MistralChat(id="mistral-large-latest")` |
| `memory_db` | `PostgresDb` — mémoire conversationnelle (table `pipeline_memories`) |
| `vector_db` | `PgVector` — recherche hybride + embedder `SentenceTransformerEmbedder(all-MiniLM-L6-v2)` |
| `contents_db` | `PostgresDb` — documents RAG bruts (table `rag_schema_contents`) |
| `schema_knowledge` | `Knowledge` (vector_db + contents_db, max_results=5) |
| `load_knowledge()` | Charge `knowledge/schema_docs.md` via `MarkdownReader` + `SemanticChunking(chunk_size=500, similarity_threshold=0.5)` |

### Agents singletons (réutilisés entre les requêtes)

| Agent | Guardrails | Mémoire | Knowledge | Tools |
|---|---|---|---|---|
| **Intent Agent** (Step 1) | `TopicGuardrail`, `SQLInjectionGuardrail`, `PromptInjectionGuardrail` | Oui | — | — |
| **RAG Schema Agent** (Step 2) | — | — | `schema_knowledge` | — |
| **DB Executor** (Step 5) | — | — | — | `execute_sql_readonly` |
| **Response Formatter** (Step 6) | `OutputSafetyGuardrail` | Oui | — | — |

### Agents dynamiques (recréés à chaque requête)

| Agent | Instructions dynamiques |
|---|---|
| **SQL Generator** (Step 3) | `build_sql_generator_instructions(allowed_tables)` — schéma limité aux tables autorisées |
| **SQL Security** (Step 4) | `build_sql_security_instructions(allowed_tables)` — validation contre les tables autorisées |

### RBAC — Constantes et fonctions

| Élément | Rôle |
|---|---|
| `ALL_TABLES` | `{"clients", "produits", "commandes"}` |
| `TABLE_SCHEMAS` | Schéma détaillé de chaque table (colonnes, types, valeurs) |
| `TABLE_RELATIONS` | Relations FK entre tables (`frozenset` comme clé) |
| `TABLE_KEYWORDS` | Mots-clés regex par table pour détecter la table visée dans la question |
| `detect_requested_tables(question)` | Détecte les tables référencées par mots-clés |
| `extract_table_names(sql)` | Extrait les tables depuis le SQL brut (regex FROM/JOIN) |
| `extract_sql(text)` | Extrait le SQL depuis un bloc markdown |
| `build_sql_generator_instructions(allowed_tables)` | Construit le prompt du SQL Generator avec tables autorisées uniquement |
| `build_sql_security_instructions(allowed_tables)` | Construit le prompt du SQL Security avec tables autorisées uniquement |

### Class-based executors (Custom Function Step Workflow)

| Classe | Step | Rôle |
|---|---|---|
| `PipelineState` | — | État partagé : `allowed_tables`, `session_id`, `sql_query` |
| `IntentExecutor` | 1 | Appelle `intent_agent.run()` avec `session_id` |
| `RAGSchemaExecutor` | 2 | Appelle `rag_schema_agent.run()` sur le résultat précédent |
| `SQLGeneratorExecutor` | 3 | Crée un `Agent` dynamique, stocke le SQL dans `state.sql_query` |
| `SQLSecurityExecutor` | 4 | Crée un `Agent` dynamique, fait le hard check regex, `StepOutput(success=False)` si rejeté |
| `DBExecutorExecutor` | 5 | Appelle `db_executor_agent.run()` |
| `ResponseFormatterExecutor` | 6 | Appelle `response_formatter_agent.run()` avec `session_id` |

### `run_pipeline(question, session_id, allowed_tables)`

1. **Pré-check RBAC** : `detect_requested_tables()` → bloque si table interdite
2. Crée un `PipelineState` et un `Workflow` avec les 6 `Step`
3. Exécute `pipeline.run(input=question)`
4. Retourne `{"response": ..., "sql_query": ...}`

---

## `backend/auth.py`

**Authentification JWT + RBAC.**

### Imports

```python
import os, re, json
from datetime import datetime, timedelta, timezone

import jwt
import bcrypt
import psycopg2
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
```

### Constantes

| Variable | Valeur |
|---|---|
| `JWT_SECRET` | env `JWT_SECRET_KEY` (défaut : `"dev-secret-key-change-in-prod"`) |
| `JWT_ALGORITHM` | `"HS256"` |
| `JWT_EXPIRATION_HOURS` | `24` |
| `ALL_TABLES` | `["clients", "produits", "commandes"]` |

### Fonctions

| Fonction | Rôle |
|---|---|
| `hash_password(password)` | Bcrypt hash (tronqué à 72 bytes) |
| `verify_password(password, hashed)` | Bcrypt check |
| `validate_email(email)` | Regex + max 200 caractères |
| `validate_password(password)` | Min 8, max 72, 1 majuscule, 1 minuscule, 1 chiffre, 1 spécial |
| `validate_username(username)` | Min 3, max 50, lettres/chiffres/espaces/tirets/underscores (accents supportés) |
| `create_token(user_id, email, role, allowed_tables)` | JWT avec expiration 24h, rôle et tables |
| `decode_token(token)` | Décode et valide le JWT |

### Dependencies FastAPI

| Dependency | Rôle |
|---|---|
| `get_current_user(credentials)` | Vérifie le token, retourne `{user_id, email, role, allowed_tables}`. Admin → toutes les tables |
| `require_admin(user)` | Vérifie `role == "admin"`, sinon HTTP 403 |

### Helpers DB

| Fonction | Rôle |
|---|---|
| `get_user_by_email(email)` | SELECT avec rôle et allowed_tables |
| `create_user(username, email, password)` | INSERT — premier utilisateur = admin automatiquement |
| `ensure_users_table()` | CREATE TABLE IF NOT EXISTS + ALTER TABLE migration RBAC |

---

## `backend/guardrails.py`

**Protection des entrées et sorties du pipeline.**

### Imports

```python
import re
from agno.guardrails import BaseGuardrail
from agno.exceptions import InputCheckError, CheckTrigger
from agno.run.agent import RunInput
```

### Catégories de guardrails

| # | Catégorie | Variable | Nombre de patterns | Détection |
|---|---|---|---|---|
| 1 | **Salutations** | `GREETING_PATTERNS` | 7 | Bonjour, hello, merci, aide, qui es-tu... |
| 2 | **Hors-sujet** | `OFF_TOPIC_PATTERNS` | ~80 | Météo, humour, cuisine, code, politique, sport, films, voyages, santé, animaux, éducation, religion, relations, mode, astrologie, géographie, sciences, immobilier, automobile, actualité, finance, bricolage, tech, réseaux sociaux |
| 3 | **SQL Injection** | `SQL_INJECTION_PATTERNS` | ~30 | DROP, DELETE, UPDATE, UNION injection, boolean injection, time-based, tables système, opérations fichiers, actions destructrices FR |
| 4 | **Prompt Injection** | `PROMPT_INJECTION_PATTERNS` | ~25 | Ignore instructions, changement rôle, jailbreak, DAN, accès prompt système, formatage injection, override |

### Double usage

**Fonctions simples** (utilisées dans `api.py` avant le pipeline) :
- `is_greeting(text)` → `bool`
- `is_off_topic(text)` → `bool`
- `is_destructive(text)` → `bool`
- `is_prompt_injection(text)` → `bool`

**Classes Agno** (utilisées comme `pre_hooks` sur les agents) :
- `TopicGuardrail` → lève `InputCheckError` si hors-sujet
- `SQLInjectionGuardrail` → lève `InputCheckError` si injection/destructif
- `PromptInjectionGuardrail` → lève `InputCheckError` si manipulation IA
- `OutputSafetyGuardrail` → masque les emails (`***@***.com`) et téléphones (`** ** ** ** **`) dans les réponses

### Patterns de données sensibles

- `EMAIL_PATTERN` — regex pour détecter les emails
- `PHONE_PATTERN` — regex pour les numéros FR (`0X XX XX XX XX`)

---

## `backend/tools.py`

**Outil d'exécution SQL appelé par le DB Executor Agent.**

### Imports

```python
import json, os
import psycopg2
from agno.tools import tool
```

### `@tool execute_sql_readonly(query: str) -> str`

1. Vérifie que la requête commence par `SELECT`
2. Vérifie l'absence de keywords dangereux : `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`
3. Ouvre une connexion `psycopg2` en mode **readonly** (`conn.set_session(readonly=True)`)
4. Exécute la requête
5. Retourne un JSON : `{"columns": [...], "rows": [...], "row_count": N}`
6. Si aucun résultat : `"Aucun résultat trouvé."`

---

## `backend/requirements.txt`

```
fastapi                  → Framework API REST
uvicorn[standard]        → Serveur ASGI
python-dotenv            → Chargement variables .env
psycopg2-binary          → Driver PostgreSQL synchrone
agno                     → Framework orchestration agents IA
mistralai                → Client API Mistral
sqlalchemy               → ORM (utilisé par Agno pour PgVector)
psycopg[binary]          → Driver PostgreSQL asynchrone (Agno)
pgvector                 → Extension PgVector Python
sentence-transformers    → Embeddings locaux (all-MiniLM-L6-v2)
chonkie[semantic]        → Chunking sémantique des documents
openai                   → Client OpenAI (optionnel)
huggingface-hub          → Hub modèles HuggingFace
transformers             → Modèles et tokenizers
tokenizers               → Tokenizers rapides
PyJWT                    → Tokens JWT
bcrypt                   → Hashing mots de passe
```

---

## `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

| Étape | Description |
|---|---|
| Image de base | `python:3.11-slim` |
| Dépendances système | `libpq-dev` + `gcc` pour compiler `psycopg2` |
| PyTorch | Version CPU-only (pour SentenceTransformers) |
| Requirements | Toutes les dépendances Python |
| Commande | `uvicorn api:app --host 0.0.0.0 --port 8000` |

---

## `frontend/src/main.tsx`

**Point d'entrée React.**

### Imports

```typescript
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
```

Monte `<App />` dans `<StrictMode>` sur l'élément `#root` défini dans `index.html`.

---

## `frontend/src/index.css`

**Variables CSS et système de thèmes.**

Définit le design system avec des CSS custom properties et deux thèmes :

| Variable | Dark (défaut) | Light |
|---|---|---|
| `--bg-primary` | `#0f172a` | `#f8fafc` |
| `--bg-secondary` | `#1e293b` | `#ffffff` |
| `--bg-tertiary` | `#334155` | `#e2e8f0` |
| `--text-primary` | `#f1f5f9` | `#0f172a` |
| `--text-secondary` | `#94a3b8` | `#475569` |
| `--text-muted` | `#64748b` | `#94a3b8` |
| `--accent` | `#10b981` | `#059669` |
| `--accent-hover` | `#34d399` | `#10b981` |
| `--user-bubble` | `#10b981` | `#059669` |
| `--bot-bubble` | `#1e293b` | `#ffffff` |
| `--border` | `#334155` | `#cbd5e1` |

Police : `'Inter', system-ui, -apple-system, sans-serif`

Le thème est appliqué via `data-theme` sur `<html>`.

---

## `frontend/src/App.tsx`

**Composant principal — Single Page Application.**

### Imports

```typescript
import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, Database, MessageSquare, User, Bot, History, Trash2, ArrowLeft,
         Copy, Check, Download, Sun, Moon, Code, LogOut, Mail, Lock,
         UserPlus, Shield, Users } from 'lucide-react'
import './App.css'
```

### Interfaces TypeScript

| Interface | Champs |
|---|---|
| `AuthUser` | `id`, `username`, `email`, `role`, `allowed_tables` |
| `AdminUser` | `AuthUser` + `created_at` |
| `Message` | `id`, `role: 'user'\|'bot'`, `content`, `error?`, `timestamp`, `sql_query?` |
| `HistoryItem` | `id`, `session_id`, `question`, `response`, `created_at` |

### Configuration API

```typescript
const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''
```

En développement : appelle directement `localhost:8000`. En Docker : Nginx proxy `/api/`.

### Vues

`'login' | 'register' | 'chat' | 'history' | 'admin'`

### State (useState)

| Groupe | Variables |
|---|---|
| Auth | `token`, `authUser`, `view`, `authError`, `authLoading` |
| Chat | `messages`, `input`, `loading`, `online`, `sessionId`, `copiedId`, `showSqlId` |
| Thème | `theme` (persisté dans `localStorage`) |
| Historique | `history`, `historyLoading` |
| Admin | `adminUsers`, `adminLoading`, `adminError`, `adminSuccess` |

### Effets (useEffect)

| Effet | Description |
|---|---|
| Thème | `document.documentElement.setAttribute('data-theme', theme)` + `localStorage` |
| Auto-scroll | Scroll vers le bas à chaque nouveau message |
| Health check | `GET /api/health` toutes les 30 secondes |
| Auto-resize | Textarea s'adapte au contenu |
| Chargement conditionnel | Historique et users admin selon la vue active |

### Fonctionnalités par vue

| Vue | Fonctionnalités |
|---|---|
| **Login** | Formulaire email/password, toggle thème, lien vers register |
| **Register** | Formulaire username/email/password, règles mot de passe affichées en badges, lien vers login |
| **Chat** | Header (status en ligne, thème, admin si rôle=admin, historique, déconnexion). Messages user/bot avec rendu Markdown, copier, export CSV, voir SQL. Suggestions cliquables si aucun message. Textarea auto-resize, envoi avec Entrée |
| **History** | Cards avec date, question et réponse (rendu Markdown). Bouton suppression globale |
| **Admin** | Cards utilisateur : avatar, nom, email, badge rôle, date. Select rôle (désactivé pour soi-même). Checkboxes tables (désactivé pour admins). Alertes succès/erreur |

### Fonctions principales

| Fonction | Rôle |
|---|---|
| `handleLogin()` | POST `/api/auth/login`, stocke token + user dans `localStorage` |
| `handleRegister()` | POST `/api/auth/register`, stocke token + user dans `localStorage` |
| `logout()` | Vide state et `localStorage` |
| `sendMessage(text)` | POST `/api/ask`, ajoute messages user/bot au state |
| `loadHistory()` | GET `/api/history?limit=50` |
| `clearHistory()` | DELETE `/api/history` (avec confirmation) |
| `loadAdminUsers()` | GET `/api/admin/users` |
| `updateUserRole(userId, role)` | PUT `/api/admin/users/{id}/role` |
| `updateUserTables(userId, tables)` | PUT `/api/admin/users/{id}/tables` |
| `toggleTable(user, table)` | Toggle une table, minimum 1 requise |
| `exportCSV(text)` | Parse tableau Markdown → télécharge CSV (UTF-8 BOM) |
| `copyMessage(id, text)` | Copie dans le clipboard avec feedback visuel |

---

## `frontend/src/App.css`

**Styles de l'application — 1230 lignes.**

| Section | Classes principales | Description |
|---|---|---|
| Layout | `.app` | Flex column, max-width 900px, height 100vh |
| Header | `.header`, `.header-left`, `.header-actions`, `.header-btn`, `.header-status` | Barre supérieure avec icône gradient, titre, sous-titre, boutons, status dot animé |
| Chat Area | `.chat-area` | Zone scrollable avec scrollbar custom |
| Welcome | `.welcome`, `.suggestions`, `.suggestion-btn` | Écran d'accueil avec icône, texte, grille 2 colonnes |
| Messages | `.message-wrapper`, `.message`, `.message-avatar`, `.message-content` | Bulles user (emerald, droite) et bot (fond secondaire, gauche), animation fade-in |
| Markdown | `.message.bot .message-content table/th/td/code/pre` | Tables avec header accent, code monospace, listes |
| Actions | `.message-actions`, `.action-btn` | Boutons copier/CSV/SQL, apparaissent au hover |
| SQL Display | `.sql-display`, `.sql-display-header`, `.sql-display-code` | Bloc accordéon avec code monospace |
| Loading | `.loading-dots` | 3 dots bounce animés |
| Input | `.input-area`, `.input-wrapper textarea`, `.send-btn` | Textarea auto-resize, border-radius 14px, bouton Send |
| Responsive | `@media (max-width: 640px)` | Padding réduit, suggestions en 1 colonne |
| History | `.history-area`, `.history-item`, `.history-question`, `.history-response` | Cards avec date, question accent, réponse |
| Light Theme | `[data-theme="light"]` | Box-shadows légères, gradients adaptés |
| Auth | `.auth-container`, `.auth-card`, `.auth-field`, `.auth-btn`, `.auth-password-rules` | Card centrée 420px, champs avec icônes, badges règles |
| Admin | `.admin-area`, `.admin-user-card`, `.admin-role-badge`, `.admin-select`, `.admin-checkbox-label` | Cards utilisateur, badge violet/vert, select, checkboxes |

---

## `frontend/package.json`

### Dépendances de production

| Package | Version | Rôle |
|---|---|---|
| `react` | ^19.2.0 | Bibliothèque UI |
| `react-dom` | ^19.2.0 | Rendu DOM |
| `react-markdown` | ^10.1.0 | Rendu Markdown dans les réponses bot |
| `remark-gfm` | ^4.0.1 | Support tables et strikethrough GFM |
| `lucide-react` | ^0.563.0 | 18 icônes SVG |

### Dépendances de développement

| Package | Version | Rôle |
|---|---|---|
| `typescript` | ~5.9.3 | Typage statique |
| `vite` | ^7.2.4 | Bundler et dev server |
| `@vitejs/plugin-react` | ^5.1.1 | Plugin React pour Vite |
| `eslint` | ^9.39.1 | Linter |
| `@types/react` | ^19.2.5 | Types TypeScript React |
| `@types/react-dom` | ^19.2.3 | Types TypeScript React DOM |

---

## `frontend/Dockerfile`

**Build multi-stage.**

```dockerfile
# Étape 1 : Build React
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Étape 2 : Servir avec Nginx
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

| Stage | Image | Rôle |
|---|---|---|
| Build | `node:20-alpine` | `npm ci` + `npm run build` (`tsc -b && vite build`) → `/app/dist` |
| Production | `nginx:alpine` | Sert les fichiers statiques + proxy API |

---

## `frontend/nginx.conf`

**Reverse proxy et SPA routing.**

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }
}
```

| Bloc | Rôle |
|---|---|
| `location /` | SPA fallback : redirige toutes les routes vers `index.html` |
| `location /api/` | Proxy vers `backend:8000` (réseau Docker interne), timeout 120s |

---

## `db/init.sql`

**Schéma de la base de données + données de test.**

Exécuté automatiquement au premier lancement Docker via `docker-entrypoint-initdb.d`.

### Extension

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Tables métier

| Table | Colonnes | Données de test |
|---|---|---|
| `produits` | `id` SERIAL PK, `nom` VARCHAR(100), `categorie` VARCHAR(50), `prix` DECIMAL(10,2) | 10 produits (Informatique, Téléphonie, Audio, Wearable) |
| `clients` | `id` SERIAL PK, `nom`, `prenom`, `email` UNIQUE, `ville`, `date_inscription`, `statut` | 12 clients dans 7 villes |
| `commandes` | `id` SERIAL PK, `client_id` FK→clients, `produit_id` FK→produits, `quantite`, `montant_total`, `date_commande`, `statut` | 20 commandes (completee, en_cours, annulee) |

### Tables système

| Table | Rôle |
|---|---|
| `users` | Authentification : `username`, `email`, `hashed_password`, `role` (défaut 'user'), `allowed_tables` (JSONB, défaut toutes) |
| `conversation_history` | Historique : `session_id`, `user_id` FK→users, `question`, `response`, `created_at`. Index sur `session_id` et `created_at DESC` |
| `rag_schema` | Embeddings RAG : `content` TEXT, `metadata` JSONB, `embedding` vector(384). Index HNSW (cosine) |

---

## `knowledge/schema_docs.md`

**Documents RAG chargés dans PgVector au démarrage.**

Fichier Markdown avec 7 documents séparés par `--- DOCUMENT ---` :

| Document | Type | Contenu |
|---|---|---|
| 1 | `database_overview` | 3 tables uniquement, pas de table "ventes" |
| 2 | `table_structure: clients` | Colonnes, types, valeurs (statut: actif/inactif) |
| 3 | `table_structure: produits` | Colonnes, types, catégories |
| 4 | `table_structure: commandes` | Colonnes, FK, statuts (completee/en_cours/annulee) |
| 5 | `relations` | FK et syntaxe JOIN |
| 6 | `business_rules` | Règles métier, calcul CA, panier moyen |
| 7 | `sql_examples` | 6 exemples de requêtes courantes |

Chunking : `SemanticChunking(chunk_size=500, similarity_threshold=0.5)`

---

## `docker-compose.yml`

**Orchestration des 3 services.**

```
┌───────────────────────────────────────────────────────────┐
│                     Docker Compose                         │
│                                                            │
│  ┌────────────┐    ┌────────────────┐    ┌─────────────┐  │
│  │     db      │    │    backend     │    │  frontend   │  │
│  │  pgvector/  │◄───│    FastAPI     │◄───│    Nginx    │  │
│  │  pg17       │    │  Python 3.11   │    │   React 19  │  │
│  │  :5433      │    │  :8000         │    │   :80       │  │
│  └────────────┘    └────────────────┘    └─────────────┘  │
│                                                            │
│  Volume: pgdata     Volume: ./knowledge                    │
└───────────────────────────────────────────────────────────┘
```

| Service | Image | Port exposé | Dépend de | Volumes |
|---|---|---|---|---|
| `db` | `pgvector/pgvector:pg17` | `5433:5432` | — | `pgdata` (données), `./db/init.sql` → `docker-entrypoint-initdb.d` |
| `backend` | Build `./backend` | `8000:8000` | `db` (healthcheck) | `./knowledge:/knowledge` |
| `frontend` | Build `./frontend` | `80:80` | `backend` | — |

### Variables d'environnement (backend)

| Variable | Source | Rôle |
|---|---|---|
| `MISTRAL_API_KEY` | `.env` | Clé API Mistral (obligatoire) |
| `OPENAI_API_KEY` | `.env` | Clé API OpenAI (optionnel) |
| `DATABASE_URL` | Hardcoded | `postgresql+psycopg://...@db:5432/...` (async, pour Agno) |
| `DATABASE_URL_PSYCOPG2` | Hardcoded | `postgresql://...@db:5432/...` (sync, pour psycopg2) |
| `JWT_SECRET_KEY` | `.env` | Secret pour signer les JWT |

### Healthcheck DB

`pg_isready -U postgres` — intervalle 5s, timeout 5s, 5 retries. Le backend attend que la DB soit saine avant de démarrer.
