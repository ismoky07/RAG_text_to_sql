"""
Skill 06 : Teams (Équipes d'Agents)
======================================
Concept Agno : Une Team est une collection d'agents qui travaillent ensemble.
Le leader de l'équipe distribue les responsabilités selon les rôles spécialisés.

3 modes : Supervisor (défaut), Router, Broadcast

Documentation : https://docs.agno.com/teams/overview
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.team import Team


# ── 1. Définir les agents spécialisés ────────────────────────────────────────
sql_expert = Agent(
    name="SQL Expert",
    role="Tu es un expert en SQL PostgreSQL. "
         "Tu génères des requêtes SQL optimisées et sécurisées.",
    model=OpenAIChat(id="gpt-4o"),
)

data_analyst = Agent(
    name="Data Analyst",
    role="Tu es un analyste de données. "
         "Tu interprètes les résultats et fournis des insights métier.",
    model=OpenAIChat(id="gpt-4o"),
)

security_reviewer = Agent(
    name="Security Reviewer",
    role="Tu es un expert en sécurité. "
         "Tu valides que les requêtes SQL sont sûres (SELECT uniquement, pas d'injection).",
    model=OpenAIChat(id="gpt-4o"),
)


# ── 2. Mode Supervisor (défaut) ──────────────────────────────────────────────
# Le leader décompose la tâche, vérifie la qualité, synthétise les résultats.

team_supervisor = Team(
    name="Data Analysis Team",
    members=[sql_expert, data_analyst, security_reviewer],
    model=OpenAIChat(id="gpt-4o"),
    instructions="Tu coordonnes l'équipe pour répondre aux questions data. "
                 "1. Le SQL Expert génère la requête. "
                 "2. Le Security Reviewer valide la sécurité. "
                 "3. Le Data Analyst interprète les résultats. "
                 "Réponds en français.",
    markdown=True,
)


# ── 3. Mode Router ───────────────────────────────────────────────────────────
# Routage direct vers le spécialiste, sans combiner les réponses.

team_router = Team(
    name="Support Router",
    members=[sql_expert, data_analyst, security_reviewer],
    model=OpenAIChat(id="gpt-4o"),
    respond_directly=True,
    determine_input_for_members=False,
    instructions="Route la question vers l'agent le plus approprié.",
    markdown=True,
)


# ── 4. Mode Broadcast ────────────────────────────────────────────────────────
# Traitement parallèle par tous les membres simultanément.

team_broadcast = Team(
    name="Review Board",
    members=[sql_expert, data_analyst, security_reviewer],
    model=OpenAIChat(id="gpt-4o"),
    delegate_to_all_members=True,
    instructions="Chaque membre donne son avis sur la question.",
    markdown=True,
)


# ── 5. Teams imbriquées (hiérarchiques) ──────────────────────────────────────
backend_team = Team(
    name="Backend Team",
    role="Équipe backend spécialisée en SQL et sécurité",
    members=[sql_expert, security_reviewer],
    model=OpenAIChat(id="gpt-4o"),
)

full_team = Team(
    name="Full Data Team",
    members=[backend_team, data_analyst],
    model=OpenAIChat(id="gpt-4o"),
    instructions="Coordonne l'équipe backend et l'analyste pour répondre aux questions.",
    markdown=True,
)


# ── 6. Exécution ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Mode Supervisor ===\n")
    team_supervisor.print_response(
        "Génère une requête SQL pour compter les clients par ville, "
        "puis analyse les résultats.",
        stream=True,
    )

    print("\n" + "=" * 60 + "\n")

    print("=== Mode Router ===\n")
    team_router.print_response(
        "Comment optimiser une requête avec des JOINs multiples ?",
        stream=True,
    )
