# AI Data Assistant

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Mistral](https://img.shields.io/badge/LLM-Mistral_Large-FF7000)

Assistant IA qui transforme vos questions en langage naturel en requêtes SQL, les exécute sur PostgreSQL et retourne des réponses compréhensibles en français.

> **Posez une question → L'IA génère le SQL → La base répond → Vous obtenez la réponse en clair**

## Aperçu

| Chat | Administration |
|---|---|
| ![Chat](docs/screenshot/chat.png) | ![Admin](docs/screenshot/Admin.png) |

---

## Fonctionnalités

- **Text-to-SQL** — Pipeline de 6 agents IA orchestrés par [Agno Workflow](https://github.com/agno-agi/agno)
- **RAG hybride** — Knowledge base vectorisée (PgVector + SentenceTransformers) pour enrichir la génération SQL
- **Mémoire conversationnelle** — Supporte les questions de suivi (*"et à Lyon ?"*)
- **RBAC 4 couches** — Contrôle d'accès par tables avec pré-check, instructions dynamiques, agent de sécurité et hard check regex
- **Guardrails** — Protection contre injection SQL, prompt injection, hors-sujet, et masquage des données sensibles en sortie
- **Panneau admin** — Gestion des rôles (admin/user) et des tables autorisées par utilisateur
- **Auth JWT + bcrypt** — Inscription avec validation robuste (email, mot de passe, username)
- **Dark / Light mode** — Thème sombre par défaut, basculement instantané
- **Export CSV** — Téléchargement des tableaux de résultats
- **Affichage SQL** — Visualisation optionnelle de la requête générée

---

## Stack technique

| Couche | Technologie |
|---|---|
| **LLM** | Mistral Large via Agno `MistralChat` |
| **Orchestration** | Agno Custom Function Step Workflow (6 agents) |
| **Embeddings** | SentenceTransformers `all-MiniLM-L6-v2` (dim 384) |
| **Backend** | FastAPI + Uvicorn (Python 3.11) |
| **Frontend** | React 19 + TypeScript + Vite 7 |
| **Base de données** | PostgreSQL 17 + PgVector (recherche hybride) |
| **Auth** | JWT (PyJWT) + bcrypt |
| **Conteneurisation** | Docker Compose (3 services) + Nginx |

---

## Démarrage rapide

### Prérequis

- **Docker** et **Docker Compose**
- Clé API **Mistral** ([mistral.ai](https://mistral.ai))

### 1. Cloner

```bash
git clone <repository-url>
cd Chatbot_RAG_Text_to_SQL
```

### 2. Configurer

Créer un fichier `.env` à la racine :

```env
MISTRAL_API_KEY=votre_clé_mistral
JWT_SECRET_KEY=votre_secret_jwt
```

### 3. Lancer

```bash
docker compose up --build -d
```

### 4. Utiliser

| URL | Description |
|---|---|
| [http://localhost](http://localhost) | Application (React + Nginx) |
| [http://localhost:8000/docs](http://localhost:8000/docs) | Documentation API Swagger |

Le **premier compte créé** devient automatiquement **administrateur**.

### Réinitialiser la base

```bash
docker compose down -v && docker compose up --build -d
```

---

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        Docker Compose                          │
│                                                                │
│  ┌────────────┐     ┌─────────────────┐     ┌──────────────┐  │
│  │     db      │     │    backend      │     │   frontend   │  │
│  │  pgvector/  │◄────│    FastAPI      │◄────│    Nginx     │  │
│  │  pg17       │     │  Python 3.11    │     │   React 19   │  │
│  │  :5433      │     │  :8000          │     │   :80        │  │
│  └────────────┘     └─────────────────┘     └──────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

### Pipeline Text-to-SQL (6 steps)

```
Question → [Guardrails] → [RBAC Pré-check]
               │
               ▼
    ┌──────────────────────┐
    │  1. Intent Agent      │  Analyse l'intention + mémoire conversationnelle
    │  2. RAG Schema Agent  │  Récupère le contexte DB via PgVector
    │  3. SQL Generator     │  Génère le SQL (instructions RBAC dynamiques)
    │  4. SQL Security      │  Valide + hard check regex sur les tables
    │  5. DB Executor       │  Exécute en lecture seule (readonly)
    │  6. Response Formatter│  Reformule en français naturel
    └──────────────────────┘
               │
               ▼
          Réponse en clair
```

> Pour l'architecture détaillée fichier par fichier (imports, fonctions, classes), voir **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

---

## Diagramme de cas d'utilisation

```mermaid
graph LR
    User((User))
    Admin((Admin))

    User --- UC1[S'inscrire]
    User --- UC2[Se connecter]
    User --- UC3[Poser une question<br/>en langage naturel]
    User --- UC4[Voir la requête SQL générée]
    User --- UC5[Exporter les résultats en CSV]
    User --- UC6[Consulter son historique]
    User --- UC7[Supprimer son historique]
    User --- UC8[Changer de thème<br/>dark / light]
    User --- UC9[Se déconnecter]

    Admin --- UC10[Voir la liste<br/>des utilisateurs]
    Admin --- UC11[Modifier le rôle<br/>d'un utilisateur]
    Admin --- UC12[Modifier les tables<br/>autorisées d'un utilisateur]

    Admin -.->|hérite de| User

    style User fill:#10b981,stroke:#059669,color:#fff
    style Admin fill:#8b5cf6,stroke:#7c3aed,color:#fff
    style UC1 fill:#1e293b,stroke:#334155,color:#f1f5f9
    style UC2 fill:#1e293b,stroke:#334155,color:#f1f5f9
    style UC3 fill:#1e293b,stroke:#334155,color:#f1f5f9
    style UC4 fill:#1e293b,stroke:#334155,color:#f1f5f9
    style UC5 fill:#1e293b,stroke:#334155,color:#f1f5f9
    style UC6 fill:#1e293b,stroke:#334155,color:#f1f5f9
    style UC7 fill:#1e293b,stroke:#334155,color:#f1f5f9
    style UC8 fill:#1e293b,stroke:#334155,color:#f1f5f9
    style UC9 fill:#1e293b,stroke:#334155,color:#f1f5f9
    style UC10 fill:#1e293b,stroke:#8b5cf6,color:#f1f5f9
    style UC11 fill:#1e293b,stroke:#8b5cf6,color:#f1f5f9
    style UC12 fill:#1e293b,stroke:#8b5cf6,color:#f1f5f9
```

---

## Flux : Poser une question

![Flux poser une question](docs/screenshot/flowAgent.png)

---

## Flux : Administration (RBAC)

```mermaid
flowchart TD
    A([Admin connecté]) --> B[Clic bouton Shield]
    B --> C[GET /api/admin/users<br/>Charger la liste]
    C --> D[Liste des utilisateurs]

    D --> E[Modifier le rôle]
    D --> F[Modifier les tables]

    E --> E1{Soi-même ?}
    E1 -->|OUI| E2[Désactivé]
    E1 -->|NON| E3[Select : admin / user]
    E3 --> E4[PUT /admin/users/id/role]

    F --> F1{Rôle admin ?}
    F1 -->|OUI| F2[Désactivé : accès total]
    F1 -->|NON| F3[Checkboxes :<br/>☐ clients ☐ produits ☐ commandes<br/>min. 1 table requise]
    F3 --> F4[PUT /admin/users/id/tables]

    E4 --> G{Succès ?}
    F4 --> G

    G -->|OUI| H[✓ Alerte succès]
    G -->|NON| I[✗ Alerte erreur]

    style A fill:#8b5cf6,stroke:#7c3aed,color:#fff
    style B fill:#1e293b,stroke:#334155,color:#f1f5f9
    style C fill:#1e293b,stroke:#334155,color:#f1f5f9
    style D fill:#1e293b,stroke:#334155,color:#f1f5f9
    style E fill:#1e293b,stroke:#334155,color:#f1f5f9
    style F fill:#1e293b,stroke:#334155,color:#f1f5f9
    style E1 fill:#f59e0b,stroke:#d97706,color:#000
    style F1 fill:#f59e0b,stroke:#d97706,color:#000
    style G fill:#f59e0b,stroke:#d97706,color:#000
    style E2 fill:#64748b,stroke:#475569,color:#fff
    style F2 fill:#64748b,stroke:#475569,color:#fff
    style E3 fill:#1e293b,stroke:#334155,color:#f1f5f9
    style E4 fill:#1e293b,stroke:#334155,color:#f1f5f9
    style F3 fill:#1e293b,stroke:#334155,color:#f1f5f9
    style F4 fill:#1e293b,stroke:#334155,color:#f1f5f9
    style H fill:#22c55e,stroke:#16a34a,color:#fff
    style I fill:#ef4444,stroke:#dc2626,color:#fff
```

---

## Structure du projet

```
Chatbot_RAG_Text_to_SQL/
├── docker-compose.yml          # Orchestration 3 services
├── .env                        # Clés API (non versionné)
├── db/
│   └── init.sql                # Schéma + données de test (12 clients, 10 produits, 20 commandes)
├── backend/
│   ├── Dockerfile              # Python 3.11 + PyTorch CPU
│   ├── requirements.txt        # 17 dépendances Python
│   ├── api.py                  # API REST FastAPI (auth, chat, historique, admin)
│   ├── agents.py               # Pipeline 6 agents Agno Workflow + RBAC
│   ├── auth.py                 # JWT + bcrypt + validation + RBAC
│   ├── guardrails.py           # 4 catégories de guardrails (140+ patterns regex)
│   └── tools.py                # Outil execute_sql_readonly
├── frontend/
│   ├── Dockerfile              # Build multi-stage (Node 20 → Nginx)
│   ├── nginx.conf              # SPA routing + proxy /api/ → backend
│   ├── package.json            # React 19, react-markdown, lucide-react
│   └── src/
│       ├── main.tsx            # Point d'entrée React
│       ├── index.css           # Variables CSS + thèmes dark/light
│       ├── App.tsx             # SPA : login, register, chat, historique, admin
│       └── App.css             # 1230 lignes de styles (responsive + thèmes)
├── knowledge/
│   └── schema_docs.md          # 7 documents RAG (schéma, règles, exemples SQL)
└── docs/
    └── ARCHITECTURE.md         # Documentation technique détaillée
```

---

## Endpoints API

| Méthode | Route | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/register` | — | Inscription |
| `POST` | `/api/auth/login` | — | Connexion |
| `GET` | `/api/auth/me` | JWT | Info utilisateur |
| `POST` | `/api/ask` | JWT | Poser une question |
| `GET` | `/api/history` | JWT | Historique |
| `DELETE` | `/api/history` | JWT | Supprimer l'historique |
| `GET` | `/api/admin/users` | Admin | Liste des utilisateurs |
| `PUT` | `/api/admin/users/{id}/role` | Admin | Modifier le rôle |
| `PUT` | `/api/admin/users/{id}/tables` | Admin | Modifier les tables autorisées |
| `GET` | `/api/health` | — | Health check |

---

## Sécurité

### RBAC — 4 couches de contrôle d'accès

| Couche | Mécanisme | Moment |
|---|---|---|
| 1 | Détection de mots-clés dans la question | Avant le pipeline |
| 2 | Instructions SQL Generator limitées aux tables autorisées | Génération SQL |
| 3 | Agent SQL Security + validation tables | Après génération |
| 4 | Hard check regex `FROM`/`JOIN` sur le SQL brut | Avant exécution |

### Guardrails — 4 catégories de protection

| Catégorie | Exemples bloqués |
|---|---|
| **Hors-sujet** (~80 patterns) | Météo, sport, cuisine, politique, code... |
| **SQL Injection** (~30 patterns) | DROP, UNION SELECT, boolean/time-based injection... |
| **Prompt Injection** (~25 patterns) | Ignore instructions, jailbreak, DAN, rôle change... |
| **Données sensibles** (sortie) | Masquage emails et téléphones |

---

## Exemples de questions

```
Combien de clients actifs y a-t-il ?
Quel est le chiffre d'affaires total ?
Quels sont les 5 produits les plus vendus ?
Quelles sont les commandes de Marie Dupont ?
Quel est le panier moyen ?
```

Questions de suivi (mémoire conversationnelle) :
```
→ Combien de clients actifs à Paris ?
← Il y a 2 clients actifs à Paris.
→ Et à Lyon ?
← Il y a 2 clients actifs à Lyon.
```

---

## Développement local

```bash
# Base de données seule
docker compose up db -d

# Backend
cd backend
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu
export MISTRAL_API_KEY=votre_clé
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5433/text_to_sql_db"
export DATABASE_URL_PSYCOPG2="postgresql://postgres:postgres@localhost:5433/text_to_sql_db"
export JWT_SECRET_KEY="dev-secret"
uvicorn api:app --reload --port 8000

# Frontend (dans un autre terminal)
cd frontend
npm install
npm run dev  # → http://localhost:5173
```
