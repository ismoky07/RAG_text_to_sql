"""
Skill 09 : Structured Output (Sortie Structurée)
===================================================
Concept Agno : Les agents peuvent retourner des objets Pydantic validés
au lieu de texte brut, grâce au paramètre output_schema.

Garantit des réponses typées, validées et exploitables programmatiquement.

Documentation : https://docs.agno.com/input-output/structured-output/agent
"""

from typing import Literal

from pydantic import BaseModel, Field

from agno.agent import Agent
from agno.models.openai import OpenAIChat


# ── 1. Schéma de sortie simple ───────────────────────────────────────────────
class SQLQuery(BaseModel):
    """Requête SQL générée à partir d'une question en langage naturel."""
    question_originale: str = Field(description="La question posée par l'utilisateur")
    intention: str = Field(description="L'intention détectée (agrégation, filtrage, etc.)")
    tables_utilisees: list[str] = Field(description="Liste des tables SQL utilisées")
    requete_sql: str = Field(description="La requête SQL générée")
    explication: str = Field(description="Explication en langage simple de la requête")


agent_sql = Agent(
    model=OpenAIChat(id="gpt-4o"),
    output_schema=SQLQuery,
    instructions="Tu es un expert Text-to-SQL. "
                 "Génère des requêtes PostgreSQL à partir de questions en langage naturel.",
)


# ── 2. Classification ────────────────────────────────────────────────────────
class IntentClassification(BaseModel):
    """Classification de l'intention de l'utilisateur."""
    category: Literal["aggregation", "filtering", "comparison", "trend", "detail"] = Field(
        description="Catégorie de l'intention"
    )
    confidence: float = Field(ge=0, le=1, description="Score de confiance (0 à 1)")
    entities: list[str] = Field(description="Entités mentionnées dans la question")
    reasoning: str = Field(description="Justification de la classification")


agent_classifier = Agent(
    model=OpenAIChat(id="gpt-4o"),
    output_schema=IntentClassification,
    instructions="Tu classes les intentions des questions métier.",
)


# ── 3. Extraction de données ─────────────────────────────────────────────────
class ClientInfo(BaseModel):
    """Informations client extraites."""
    name: str = Field(description="Nom du client")
    email: str | None = Field(None, description="Email si mentionné")
    company: str | None = Field(None, description="Entreprise si mentionnée")
    needs: list[str] = Field(default_factory=list, description="Besoins exprimés")


class ClientExtractionResult(BaseModel):
    """Résultat d'extraction de clients."""
    clients: list[ClientInfo] = Field(description="Liste des clients extraits")
    total_count: int = Field(description="Nombre total de clients trouvés")


agent_extractor = Agent(
    model=OpenAIChat(id="gpt-4o"),
    output_schema=ClientExtractionResult,
    instructions="Tu extrais les informations clients à partir de texte brut.",
)


# ── 4. Validation de sécurité SQL ────────────────────────────────────────────
class SecurityCheck(BaseModel):
    """Résultat de la vérification de sécurité SQL."""
    is_safe: bool = Field(description="True si la requête est sûre")
    risk_level: Literal["low", "medium", "high", "critical"] = Field(
        description="Niveau de risque"
    )
    issues: list[str] = Field(default_factory=list, description="Problèmes détectés")
    sanitized_query: str | None = Field(None, description="Requête corrigée si nécessaire")


agent_security = Agent(
    model=OpenAIChat(id="gpt-4o"),
    output_schema=SecurityCheck,
    instructions="Tu analyses la sécurité des requêtes SQL. "
                 "Vérifie : injection SQL, opérations dangereuses, tables non autorisées.",
)


# ── 5. Override par exécution ─────────────────────────────────────────────────
# On peut changer le schéma de sortie à chaque exécution.

agent_flexible = Agent(
    model=OpenAIChat(id="gpt-4o"),
)


# ── 6. Exécution ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Génération SQL structurée
    print("=== Génération SQL Structurée ===\n")
    response = agent_sql.run(
        "Combien de clients ont acheté le produit X en 2025 ?"
    )
    result: SQLQuery = response.content
    print(f"Question : {result.question_originale}")
    print(f"Intention : {result.intention}")
    print(f"Tables : {result.tables_utilisees}")
    print(f"SQL : {result.requete_sql}")
    print(f"Explication : {result.explication}")

    print("\n" + "=" * 60 + "\n")

    # Classification
    print("=== Classification d'intention ===\n")
    response = agent_classifier.run(
        "Quelle est l'évolution des ventes par trimestre en 2024 ?"
    )
    intent: IntentClassification = response.content
    print(f"Catégorie : {intent.category}")
    print(f"Confiance : {intent.confidence}")
    print(f"Entités : {intent.entities}")

    print("\n" + "=" * 60 + "\n")

    # Sécurité SQL
    print("=== Vérification de sécurité SQL ===\n")
    response = agent_security.run(
        "SELECT * FROM clients; DROP TABLE clients;--"
    )
    check: SecurityCheck = response.content
    print(f"Sûr : {check.is_safe}")
    print(f"Risque : {check.risk_level}")
    print(f"Problèmes : {check.issues}")

    print("\n" + "=" * 60 + "\n")

    # Override par exécution
    print("=== Override par exécution ===\n")
    response = agent_flexible.run(
        "Analyse le sentiment : 'Ce produit est excellent !'",
        output_schema=IntentClassification,
    )
    print(f"Résultat : {response.content}")
