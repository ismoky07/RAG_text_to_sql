"""
Text-to-SQL Pipeline : Agents + Workflow
=========================================
6 agents séquentiels orchestrés par un Workflow Agno.

Question utilisateur → Intent → RAG Schema → SQL Generator → SQL Security → DB Executor → Response Formatter → Réponse
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from agno.agent import Agent
from agno.models.mistral import MistralChat
from agno.workflow import Workflow
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType
from agno.knowledge.embedder.sentence_transformer import SentenceTransformerEmbedder
from agno.knowledge.reader.markdown_reader import MarkdownReader
from agno.knowledge.chunking.semantic import SemanticChunking
from agno.db.postgres import PostgresDb

from tools import execute_sql_readonly

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
DB_URL = os.getenv("DATABASE_URL")
DB_URL_PSYCOPG2 = os.getenv("DATABASE_URL_PSYCOPG2")
KNOWLEDGE_PATH = Path(__file__).parent.parent / "knowledge" / "schema_docs.md"


def get_model():
    """Retourne le modèle Mistral configuré."""
    return MistralChat(
        id="mistral-large-latest",
        api_key=MISTRAL_API_KEY,
    )


# ══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE BASE (RAG Schema)
# ══════════════════════════════════════════════════════════════════════════════

# 1. Vector DB (PgVector + SentenceTransformer)
vector_db = PgVector(
    table_name="rag_schema_vectors",
    db_url=DB_URL,
    search_type=SearchType.hybrid,
    embedder=SentenceTransformerEmbedder(id="sentence-transformers/all-MiniLM-L6-v2"),
)

# 2. Contents DB (stockage des documents bruts)
contents_db = PostgresDb(
    db_url=DB_URL,
    knowledge_table="rag_schema_contents",
)

# 3. Knowledge Base
schema_knowledge = Knowledge(
    name="SQL Schema Knowledge",
    vector_db=vector_db,
    contents_db=contents_db,
    max_results=5,
)

# 4. Chargement du schema_docs.md
async def load_knowledge():
    """Charge les documents RAG depuis le fichier Markdown."""
    await schema_knowledge.add_content_async(
        path=str(KNOWLEDGE_PATH),
        reader=MarkdownReader(
            chunking_strategy=SemanticChunking(
                chunk_size=500,
                similarity_threshold=0.5,
            )
        ),
    )
    print(f"[KB] Knowledge chargée depuis {KNOWLEDGE_PATH.name}")


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 1 : Intent Agent
# ══════════════════════════════════════════════════════════════════════════════

intent_agent = Agent(
    name="Intent Agent",
    model=get_model(),
    description="Analyse et comprend la question de l'utilisateur.",
    instructions="""Tu analyses la question de l'utilisateur et extrais :
    - L'intention : agrégation, filtrage, comparaison, tendance, détail
    - Les entités : tables, colonnes, valeurs mentionnées
    - Les contraintes : temporelles, géographiques, etc.

    Retourne une analyse structurée en texte clair.
    Exemple :
    Intention : agrégation (comptage)
    Entités : table clients, colonne ville, valeur "Paris", colonne statut, valeur "actif"
    Contraintes : aucune contrainte temporelle

    Ne génère PAS de SQL. Tu analyses uniquement la question.""",
    markdown=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 2 : RAG Schema Agent
# ══════════════════════════════════════════════════════════════════════════════

rag_schema_agent = Agent(
    name="RAG Schema Agent",
    model=get_model(),
    description="Fournit le contexte technique (schéma DB, règles métier, exemples SQL).",
    knowledge=schema_knowledge,
    search_knowledge=True,
    instructions="""À partir de l'analyse d'intention fournie, recherche dans ta knowledge base :
    - La structure des tables pertinentes (colonnes, types, valeurs possibles)
    - Les relations entre tables (clés étrangères, JOINs)
    - Les règles métier applicables
    - Les exemples SQL similaires

    Retourne le contexte technique complet qui permettra de générer le SQL.
    Ne génère PAS de SQL toi-même. Tu fournis uniquement le contexte.""",
    markdown=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 3 : SQL Generator
# ══════════════════════════════════════════════════════════════════════════════

sql_generator_agent = Agent(
    name="SQL Generator",
    model=get_model(),
    description="Génère une requête SQL PostgreSQL à partir de l'intention et du contexte schéma.",
    instructions="""À partir de l'intention analysée et du contexte schéma fourni, génère UNE requête SQL PostgreSQL.

    TABLES DISPONIBLES (il n'en existe AUCUNE autre) :
    - clients (id, nom, prenom, email, ville, date_inscription, statut)
      → statut : UNIQUEMENT 'actif' ou 'inactif' (PAS 'active', 'inactive' ou autre)
    - produits (id, nom, categorie, prix)
    - commandes (id, client_id, produit_id, quantite, montant_total, date_commande, statut)
      → statut : UNIQUEMENT 'completee', 'en_cours' ou 'annulee' (PAS 'livree', 'delivered', 'pending' ou autre)

    RELATIONS :
    - commandes.client_id → clients.id
    - commandes.produit_id → produits.id

    ATTENTION :
    - Il n'existe PAS de table "ventes", "details_commande", "orders" ou autre.
    - Les ventes/achats sont dans la table "commandes".
    - Le chiffre d'affaires = SUM(montant_total) WHERE statut = 'completee'
    - N'ajoute PAS de conditions qui ne sont pas demandées (pas de filtre temporel si non demandé).
    - Traduis EXACTEMENT la question en SQL, rien de plus.

    Règles strictes :
    - SELECT uniquement (jamais INSERT, UPDATE, DELETE, DROP)
    - Une seule requête
    - Utilise UNIQUEMENT les 3 tables ci-dessus
    - Utilise UNIQUEMENT les valeurs de statut listées ci-dessus
    - Utilise des alias lisibles (AS nom_colonne)
    - PostgreSQL syntax uniquement
    - Utilise les JOINs corrects selon les relations ci-dessus

    Retourne UNIQUEMENT la requête SQL, sans explication.
    Format : la requête SQL brute, rien d'autre.""",
    markdown=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 4 : SQL Security Agent
# ══════════════════════════════════════════════════════════════════════════════

sql_security_agent = Agent(
    name="SQL Security Agent",
    model=get_model(),
    description="Valide la sécurité de la requête SQL générée.",
    instructions="""Tu reçois une requête SQL. Vérifie :

    1. C'est un SELECT uniquement (pas de DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE)
    2. Pas de sous-requêtes destructrices
    3. Pas de tentative d'injection SQL (commentaires --, ;, UNION non justifié)
    4. Les tables référencées sont valides : clients, produits, commandes
    5. Pas d'accès à des tables système (pg_*, information_schema)

    Si la requête est SÛRE : retourne la requête SQL telle quelle, sans modification.
    Si la requête est DANGEREUSE : retourne "REJETÉE : " suivi de l'explication du problème.""",
    markdown=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 5 : DB Executor
# ══════════════════════════════════════════════════════════════════════════════

db_executor_agent = Agent(
    name="DB Executor",
    model=get_model(),
    description="Exécute la requête SQL validée sur la base de données.",
    tools=[execute_sql_readonly],
    instructions="""Tu reçois une requête SQL validée.

    Si le message contient "REJETÉE" : ne fais rien, transmets le message de rejet.

    Sinon : utilise l'outil execute_sql_readonly pour exécuter la requête.
    Retourne le résultat brut (JSON avec colonnes et lignes).""",
    markdown=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 6 : Response Formatter
# ══════════════════════════════════════════════════════════════════════════════

response_formatter_agent = Agent(
    name="Response Formatter",
    model=get_model(),
    description="Reformule les résultats SQL en réponse métier compréhensible.",
    instructions="""Tu reçois les résultats d'une requête SQL (JSON avec colonnes et lignes).

    Reformule en langage naturel français, compréhensible pour un non-technicien.

    Règles :
    - Réponds en français courant
    - Utilise des tableaux Markdown si plus de 2 lignes de résultats
    - Arrondis les montants à 2 décimales avec le symbole €
    - Ajoute un bref résumé / insight si pertinent
    - Ne montre PAS la requête SQL
    - Si le résultat est une erreur, explique poliment le problème

    Exemple :
    "Il y a 10 clients actifs à Paris. C'est la ville avec le plus de clients dans la base."
    """,
    markdown=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# WORKFLOW SÉQUENTIEL
# ══════════════════════════════════════════════════════════════════════════════

text_to_sql_workflow = Workflow(
    name="Text-to-SQL Pipeline",
    steps=[
        intent_agent,
        rag_schema_agent,
        sql_generator_agent,
        sql_security_agent,
        db_executor_agent,
        response_formatter_agent,
    ],
)


# ══════════════════════════════════════════════════════════════════════════════
# TEST
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio

    async def main():
        # Charger la knowledge base
        await load_knowledge()

        # Tester le pipeline
        print("=" * 60)
        print("Test du pipeline Text-to-SQL")
        print("=" * 60)

        questions = [
            "Combien de clients actifs sont à Paris ?",
            "Quel est le chiffre d'affaires total ?",
            "Quelles sont les commandes de Marie Dupont ?",
        ]

        for question in questions:
            print(f"\n{'─' * 60}")
            print(f"Question : {question}")
            print(f"{'─' * 60}")
            text_to_sql_workflow.print_response(question, stream=True)

    asyncio.run(main())
