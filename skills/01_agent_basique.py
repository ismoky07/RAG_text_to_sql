"""
Skill 01 : Agent Basique
=========================
Concept Agno : Créer un agent simple avec un modèle, des instructions et des outils.

Un Agent est une boucle de contrôle avec état autour d'un modèle sans état.
Le modèle raisonne et appelle des outils en boucle, guidé par des instructions.

Documentation : https://docs.agno.com/agents/building-agents
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat

# ── 1. Agent minimal ─────────────────────────────────────────────────────────
agent_minimal = Agent(
    model=OpenAIChat(id="gpt-4o"),
    markdown=True,
)

# ── 2. Agent avec instructions ────────────────────────────────────────────────
agent_avec_instructions = Agent(
    model=OpenAIChat(id="gpt-4o"),
    instructions="Tu es un assistant spécialisé en analyse de données. "
                 "Réponds toujours en français. "
                 "Sois concis et précis.",
    markdown=True,
)

# ── 3. Agent avec description et rôle ────────────────────────────────────────
agent_complet = Agent(
    name="DataAnalyst",
    description="Un agent spécialisé en analyse de données clients",
    role="Analyste de données",
    model=OpenAIChat(id="gpt-4o"),
    instructions=[
        "Tu analyses les données clients",
        "Tu fournis des insights actionnables",
        "Tu réponds toujours en français",
    ],
    markdown=True,
)


# ── 4. Exécution ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Exécution simple
    agent_minimal.print_response("Bonjour, qui es-tu ?", stream=True)

    print("\n" + "=" * 60 + "\n")

    # Exécution avec instructions
    agent_avec_instructions.print_response(
        "Quelles sont les étapes d'une analyse de données ?",
        stream=True,
    )

    print("\n" + "=" * 60 + "\n")

    # Exécution agent complet
    agent_complet.print_response(
        "Comment segmenter une base clients ?",
        stream=True,
    )
