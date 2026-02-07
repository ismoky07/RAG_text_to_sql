"""
Skill 04 : Memory (Mémoire)
=============================
Concept Agno : La mémoire permet aux agents de retenir des informations
sur les utilisateurs entre les interactions.

Memory stocke des faits appris ("Sarah préfère les emails").
Storage stocke l'historique des conversations pour la continuité.

Documentation : https://docs.agno.com/memory/overview
"""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIChat


# ── 1. Mémoire automatique ───────────────────────────────────────────────────
# Le système extrait et stocke automatiquement les infos après chaque conversation.

db = SqliteDb(db_file="tmp/agno_memory.db")

agent_auto_memory = Agent(
    model=OpenAIChat(id="gpt-4o"),
    db=db,
    update_memory_on_run=True,  # Mémoire automatique activée
    instructions="Tu es un assistant personnel. "
                 "Tu te souviens des préférences de l'utilisateur. "
                 "Réponds en français.",
    markdown=True,
)


# ── 2. Mémoire agentique ─────────────────────────────────────────────────────
# L'agent contrôle lui-même la gestion de sa mémoire via des outils intégrés.

agent_agentic_memory = Agent(
    model=OpenAIChat(id="gpt-4o"),
    db=db,
    enable_agentic_memory=True,  # L'agent décide quoi mémoriser
    instructions="Tu es un assistant intelligent. "
                 "Tu décides quelles informations sont importantes à retenir.",
    markdown=True,
)


# ── 3. Mémoire avec PostgreSQL (production) ──────────────────────────────────
# from agno.db.postgres import PostgresDb
#
# db_pg = PostgresDb(
#     db_url="postgresql://user:password@localhost:5432/mydb",
#     memory_table="agent_memories",
# )
#
# agent_pg_memory = Agent(
#     model=OpenAIChat(id="gpt-4o"),
#     db=db_pg,
#     update_memory_on_run=True,
# )


# ── 4. Récupération manuelle des mémoires ────────────────────────────────────
def show_user_memories(agent: Agent, user_id: str):
    """Afficher les mémoires stockées pour un utilisateur."""
    memories = agent.get_user_memories(user_id=user_id)
    print(f"\nMémoires pour l'utilisateur '{user_id}':")
    for mem in memories:
        print(f"  - {mem}")
    return memories


# ── 5. Exécution ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Mémoire Automatique ===\n")

    # L'agent extrait automatiquement les infos importantes
    agent_auto_memory.print_response(
        "Je m'appelle Ahmed et je travaille dans la finance. "
        "Je préfère les rapports au format PDF.",
        user_id="ahmed_123",
        stream=True,
    )

    print("\n" + "=" * 60 + "\n")

    # L'agent se souvient des préférences
    agent_auto_memory.print_response(
        "Quel format de rapport me recommandes-tu ?",
        user_id="ahmed_123",
        stream=True,
    )

    print("\n" + "=" * 60 + "\n")

    # Afficher les mémoires stockées
    show_user_memories(agent_auto_memory, "ahmed_123")
