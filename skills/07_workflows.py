"""
Skill 07 : Workflows
======================
Concept Agno : Les Workflows orchestrent agents, teams et fonctions
à travers des étapes définies pour des tâches répétables.

Chaque étape produit une sortie qui alimente l'étape suivante.
C'est le pattern idéal pour un pipeline séquentiel comme le Text-to-SQL.

Documentation : https://docs.agno.com/workflows/overview
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.workflow import Workflow


# ── 1. Workflow simple (2 agents séquentiels) ────────────────────────────────
researcher = Agent(
    name="Researcher",
    instructions="Tu recherches des informations pertinentes sur le sujet. "
                 "Fournis des faits et données clés.",
    model=OpenAIChat(id="gpt-4o"),
)

writer = Agent(
    name="Writer",
    instructions="Tu rédiges un article clair et engageant "
                 "basé sur les recherches fournies. Réponds en français.",
    model=OpenAIChat(id="gpt-4o"),
)

content_workflow = Workflow(
    name="Content Creation",
    steps=[researcher, writer],
)


# ── 2. Workflow Text-to-SQL (pipeline complet) ───────────────────────────────
# Reproduit l'architecture du design document

intent_agent = Agent(
    name="Intent Agent",
    instructions="Tu analyses la question de l'utilisateur et extrais : "
                 "- L'intention (agrégation, filtrage, comparaison...) "
                 "- Les entités mentionnées (tables, colonnes, valeurs) "
                 "- Les contraintes temporelles "
                 "Retourne un JSON structuré.",
    model=OpenAIChat(id="gpt-4o"),
)

sql_generator = Agent(
    name="SQL Generator",
    instructions="À partir de l'intention structurée, génère une requête SQL "
                 "PostgreSQL valide. Règles : "
                 "- SELECT uniquement "
                 "- Une seule requête "
                 "- Utilise des alias lisibles "
                 "- Ajoute des commentaires SQL",
    model=OpenAIChat(id="gpt-4o"),
)

sql_security = Agent(
    name="SQL Security Agent",
    instructions="Valide la sécurité de la requête SQL : "
                 "- Vérifie que c'est un SELECT uniquement "
                 "- Pas de DROP, DELETE, UPDATE, INSERT "
                 "- Pas d'injection SQL "
                 "- Tables autorisées uniquement "
                 "Si valide, retourne la requête. Sinon, explique le problème.",
    model=OpenAIChat(id="gpt-4o"),
)

response_formatter = Agent(
    name="Response Formatter",
    instructions="Tu reformules les résultats SQL en langage métier "
                 "compréhensible pour un non-technicien. "
                 "Utilise des tableaux Markdown si approprié. "
                 "Réponds en français.",
    model=OpenAIChat(id="gpt-4o"),
)

text_to_sql_workflow = Workflow(
    name="Text-to-SQL Pipeline",
    steps=[intent_agent, sql_generator, sql_security, response_formatter],
)


# ── 3. Workflow avec fonctions custom ─────────────────────────────────────────
def validate_input(input_text: str) -> str:
    """Étape de validation d'entrée."""
    if len(input_text.strip()) < 5:
        return "Erreur : La question est trop courte. Veuillez reformuler."
    return f"Question validée : {input_text}"


workflow_with_function = Workflow(
    name="Validated Pipeline",
    steps=[validate_input, intent_agent, sql_generator],
)


# ── 4. Exécution ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Workflow Content Creation ===\n")
    content_workflow.print_response(
        "Les tendances de l'IA en 2025",
        stream=True,
    )

    print("\n" + "=" * 60 + "\n")

    print("=== Workflow Text-to-SQL ===\n")
    text_to_sql_workflow.print_response(
        "Combien de clients ont acheté le produit X en 2025 ?",
        stream=True,
    )
