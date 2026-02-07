"""
Skill 12 : Human-in-the-Loop (HITL)
======================================
Concept Agno : Le HITL permet d'intégrer la supervision humaine
dans les workflows des agents. L'agent peut demander :
- Une confirmation avant d'exécuter un outil sensible
- Un input utilisateur pendant l'exécution

Documentation : https://docs.agno.com/hitl/overview
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools import tool


# ── 1. Outils sensibles nécessitant confirmation ─────────────────────────────
@tool
def execute_sql_query(query: str) -> str:
    """Exécuter une requête SQL sur la base de données.

    Args:
        query (str): La requête SQL à exécuter.
    """
    # Simulation d'exécution
    return f"Résultat de la requête : 42 lignes retournées pour '{query}'"


@tool
def send_report_email(recipient: str, subject: str) -> str:
    """Envoyer un rapport par email.

    Args:
        recipient (str): L'adresse email du destinataire.
        subject (str): Le sujet de l'email.
    """
    return f"Email envoyé à {recipient} avec le sujet '{subject}'"


# ── 2. Agent avec HITL - Confirmation utilisateur ────────────────────────────
agent_hitl = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[execute_sql_query, send_report_email],
    instructions="Tu es un assistant data. "
                 "Avant d'exécuter une requête SQL ou d'envoyer un email, "
                 "décris ce que tu vas faire. "
                 "Réponds en français.",
    markdown=True,
)


# ── 3. Boucle HITL manuelle ──────────────────────────────────────────────────
def run_with_confirmation():
    """Exécute l'agent avec confirmation humaine pour les outils sensibles."""
    run_response = agent_hitl.run(
        "Exécute une requête pour compter les clients actifs, "
        "puis envoie le rapport à admin@company.com"
    )

    # Vérifier s'il y a des actions en attente de confirmation
    if hasattr(run_response, "active_requirements") and run_response.active_requirements:
        for requirement in run_response.active_requirements:
            if hasattr(requirement, "needs_confirmation") and requirement.needs_confirmation:
                print(f"\nAction demandée : {requirement}")
                confirmation = input("Approuver ? (o/n) : ")
                if confirmation.lower() == "o":
                    requirement.confirm()
                else:
                    requirement.reject()
                    print("Action rejetée.")

        # Reprendre l'exécution après confirmation
        response = agent_hitl.continue_run(run_response=run_response)
        print(f"\nRéponse finale : {response.content}")
    else:
        print(f"\nRéponse : {run_response.content}")


# ── 4. Pattern HITL avec streaming ───────────────────────────────────────────
async def run_with_streaming_hitl():
    """Exécute l'agent avec HITL et streaming."""
    for run_event in agent_hitl.run(
        "Analyse les ventes du mois dernier",
        stream=True,
    ):
        if hasattr(run_event, "is_paused") and run_event.is_paused:
            for requirement in run_event.active_requirements:
                print(f"\nPause : {requirement}")
                # Gérer la confirmation...
        elif hasattr(run_event, "content") and run_event.content:
            print(run_event.content, end="")


# ── 5. Pattern de validation manuelle ─────────────────────────────────────────
def validated_sql_pipeline(question: str):
    """Pipeline Text-to-SQL avec validation humaine à chaque étape."""

    # Étape 1 : Générer la requête
    sql_agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        instructions="Génère une requête SQL PostgreSQL SELECT pour cette question.",
    )
    response = sql_agent.run(question)
    generated_sql = response.content

    print(f"Requête générée :\n{generated_sql}\n")

    # Étape 2 : Confirmation humaine
    approval = input("Approuver cette requête ? (o/n/modifier) : ")

    if approval.lower() == "n":
        print("Requête annulée.")
        return None
    elif approval.lower() == "modifier":
        generated_sql = input("Entrez la requête corrigée : ")

    # Étape 3 : Exécuter
    print(f"\nExécution de : {generated_sql}")
    return execute_sql_query(generated_sql)


# ── 6. Exécution ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Human-in-the-Loop : Validation SQL ===\n")
    result = validated_sql_pipeline(
        "Combien de clients ont acheté le produit X en 2025 ?"
    )
    if result:
        print(f"\nRésultat : {result}")
