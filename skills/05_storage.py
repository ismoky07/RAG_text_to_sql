"""
Skill 05 : Storage (Base de Données / Persistance)
=====================================================
Concept Agno : Le storage fournit la persistance pour les agents :
historique des conversations, sessions, état, mémoire et traçabilité.

Agno supporte 13+ fournisseurs de bases de données.

Documentation : https://docs.agno.com/database/overview
"""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIChat


# ── 1. Storage SQLite (développement) ────────────────────────────────────────
db_sqlite = SqliteDb(db_file="tmp/agent_storage.db")

agent_sqlite = Agent(
    model=OpenAIChat(id="gpt-4o"),
    db=db_sqlite,
    add_history_to_context=True,  # Inclure l'historique dans le contexte
    num_history_runs=3,           # Garder les 3 dernières conversations
    instructions="Tu es un assistant de projet. "
                 "Tu te souviens du contexte des conversations précédentes. "
                 "Réponds en français.",
    markdown=True,
)


# ── 2. Storage PostgreSQL (production) ────────────────────────────────────────
# from agno.db.postgres import PostgresDb
#
# db_postgres = PostgresDb(
#     db_url="postgresql://user:password@localhost:5432/mydb",
# )
#
# agent_postgres = Agent(
#     model=OpenAIChat(id="gpt-4o"),
#     db=db_postgres,
#     add_history_to_context=True,
#     num_history_runs=5,
# )


# ── 3. Storage PostgreSQL Asynchrone ─────────────────────────────────────────
# from agno.db.postgres import AsyncPostgresDb
#
# db_async = AsyncPostgresDb(
#     db_url="postgresql+psycopg_async://user:password@localhost:5432/mydb",
# )
#
# agent_async = Agent(
#     model=OpenAIChat(id="gpt-4o"),
#     db=db_async,
# )


# ── 4. Sessions persistantes ─────────────────────────────────────────────────
# Les sessions permettent de reprendre une conversation.

def demo_sessions():
    """Démonstration des sessions persistantes."""
    session_id = "projet_alpha_001"

    # Première interaction
    agent_sqlite.print_response(
        "Je travaille sur le projet Alpha. "
        "C'est une app web avec FastAPI et React.",
        session_id=session_id,
        stream=True,
    )

    print("\n--- Nouvelle interaction, même session ---\n")

    # Deuxième interaction (l'agent se souvient)
    agent_sqlite.print_response(
        "Quels tests devrais-je écrire pour mon projet ?",
        session_id=session_id,
        stream=True,
    )


# ── 5. Storage pour Teams et Workflows ───────────────────────────────────────
# from agno.team import Team
# from agno.workflow import Workflow
#
# team = Team(db=db_sqlite, ...)
# workflow = Workflow(db=db_sqlite, ...)


# ── 6. Exécution ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Storage SQLite - Sessions Persistantes ===\n")
    demo_sessions()
