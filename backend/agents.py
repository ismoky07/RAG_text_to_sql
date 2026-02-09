"""
Text-to-SQL Pipeline : Agents + Workflow
=========================================
6 steps orchestrés par un Workflow Agno avec des class-based executors.

Question utilisateur → Intent → RAG Schema → SQL Generator → SQL Security → DB Executor → Response Formatter → Réponse
"""

import os
import re
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
# CONFIGURATION DE LA MÉMOIRE (PostgreSQL)
# ══════════════════════════════════════════════════════════════════════════════

memory_db = PostgresDb(
    db_url=DB_URL,
    memory_table="pipeline_memories",
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
    pre_hooks=[
        TopicGuardrail(),
        SQLInjectionGuardrail(),
        PromptInjectionGuardrail(),
    ],
    db=memory_db,
    enable_agentic_memory=True,
    add_history_to_context=True,
    instructions="""Tu analyses la question de l'utilisateur et extrais :
    - L'intention : agrégation, filtrage, comparaison, tendance, détail
    - Les entités : tables, colonnes, valeurs mentionnées
    - Les contraintes : temporelles, géographiques, etc.

    IMPORTANT : Si la question est une question de suivi (ex: "et à Lyon ?", "et pour les inactifs ?"),
    utilise l'historique de la conversation pour comprendre le contexte complet.
    Par exemple, si l'utilisateur a demandé "Combien de clients actifs à Paris ?" puis "et à Lyon ?",
    tu dois comprendre qu'il veut "Combien de clients actifs à Lyon ?".

    Retourne une analyse structurée en texte clair.
    Exemple :
    Intention : agrégation (comptage)
    Entités : table clients, colonne ville, valeur "Paris", colonne statut, valeur "actif"
    Contraintes : aucune contrainte temporelle

    Ne génère PAS de SQL. Tu analyses uniquement la question.""",
    markdown=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 2 : RAG Schema Agent (singleton)
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
# AGENT 5 : DB Executor (singleton)
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
    pre_hooks=[OutputSafetyGuardrail()],
    db=memory_db,
    enable_agentic_memory=True,
    add_history_to_context=True,
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
# RBAC : DÉFINITIONS DES TABLES (pour instructions dynamiques)
# ══════════════════════════════════════════════════════════════════════════════

ALL_TABLES = {"clients", "produits", "commandes"}

TABLE_SCHEMAS = {
    "clients": "- clients (id, nom, prenom, email, ville, date_inscription, statut)\n      → statut : UNIQUEMENT 'actif' ou 'inactif'",
    "produits": "- produits (id, nom, categorie, prix)",
    "commandes": "- commandes (id, client_id, produit_id, quantite, montant_total, date_commande, statut)\n      → statut : UNIQUEMENT 'completee', 'en_cours' ou 'annulee'",
}

TABLE_RELATIONS = {
    frozenset({"clients", "commandes"}): "- commandes.client_id → clients.id",
    frozenset({"produits", "commandes"}): "- commandes.produit_id → produits.id",
}


def build_sql_generator_instructions(allowed_tables: list[str]) -> str:
    """Construit les instructions du SQL Generator limitées aux tables autorisées."""
    table_lines = "\n    ".join(
        TABLE_SCHEMAS[t] for t in allowed_tables if t in TABLE_SCHEMAS
    )

    relation_lines = []
    allowed_set = set(allowed_tables)
    for table_pair, relation in TABLE_RELATIONS.items():
        if table_pair.issubset(allowed_set):
            relation_lines.append(relation)
    relations_section = "\n    ".join(relation_lines) if relation_lines else "Aucune relation disponible."

    disallowed = ALL_TABLES - allowed_set
    disallowed_note = ""
    if disallowed:
        disallowed_note = f"\n\n    INTERDIT : Tu n'as PAS accès aux tables suivantes : {', '.join(sorted(disallowed))}. Ne génère JAMAIS de SQL les référençant."

    return f"""À partir de l'intention analysée et du contexte schéma fourni, génère UNE requête SQL PostgreSQL.

    TABLES DISPONIBLES (il n'en existe AUCUNE autre) :
    {table_lines}

    RELATIONS :
    {relations_section}
    {disallowed_note}

    ATTENTION :
    - Il n'existe PAS de table "ventes", "details_commande", "orders" ou autre.
    - Les ventes/achats sont dans la table "commandes".
    - Le chiffre d'affaires = SUM(montant_total) WHERE statut = 'completee'
    - N'ajoute PAS de conditions qui ne sont pas demandées.
    - Traduis EXACTEMENT la question en SQL, rien de plus.

    Règles strictes :
    - SELECT uniquement (jamais INSERT, UPDATE, DELETE, DROP)
    - Une seule requête
    - Utilise UNIQUEMENT les tables listées ci-dessus
    - PostgreSQL syntax uniquement
    - Utilise des alias lisibles (AS nom_colonne)
    - Utilise les JOINs corrects selon les relations ci-dessus

    Retourne UNIQUEMENT la requête SQL, sans explication.
    Format : la requête SQL brute, rien d'autre."""


def build_sql_security_instructions(allowed_tables: list[str]) -> str:
    """Construit les instructions du SQL Security Agent limitées aux tables autorisées."""
    table_list = ", ".join(allowed_tables)
    return f"""Tu reçois une requête SQL. Vérifie :

    1. C'est un SELECT uniquement (pas de DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE)
    2. Pas de sous-requêtes destructrices
    3. Pas de tentative d'injection SQL (commentaires --, ;, UNION non justifié)
    4. Les tables référencées sont UNIQUEMENT parmi : {table_list}
    5. Pas d'accès à des tables système (pg_*, information_schema)
    6. AUCUNE référence à des tables non autorisées

    Si la requête est SÛRE : retourne la requête SQL telle quelle, sans modification.
    Si la requête est DANGEREUSE ou référence des tables non autorisées : retourne "REJETÉE : " suivi de l'explication du problème."""


def extract_table_names(sql: str) -> set[str]:
    """Extrait les noms de tables depuis une requête SQL (défense en profondeur)."""
    tables = set()
    patterns = [
        r'\bFROM\s+([a-zA-Z_]\w*)',
        r'\bJOIN\s+([a-zA-Z_]\w*)',
    ]
    for pattern in patterns:
        for match in re.findall(pattern, sql, re.IGNORECASE):
            tables.add(match.lower())
    return tables & ALL_TABLES


def extract_sql(text: str) -> str:
    """Extrait la requête SQL du texte (enlève le markdown si présent)."""
    match = re.search(r"```(?:sql)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


# ══════════════════════════════════════════════════════════════════════════════
# CLASS-BASED EXECUTORS (Custom Function Step Workflow)
# ══════════════════════════════════════════════════════════════════════════════


class PipelineState:
    """État partagé entre les steps du workflow."""
    def __init__(self, allowed_tables: list[str], session_id: str | None = None):
        self.allowed_tables = allowed_tables
        self.session_id = session_id
        self.sql_query: str | None = None


class IntentExecutor:
    """Step 1 : Analyse l'intention de la question."""
    def __init__(self, state: PipelineState):
        self.state = state

    def __call__(self, step_input: StepInput) -> StepOutput:
        response = intent_agent.run(step_input.input, session_id=self.state.session_id)
        return StepOutput(content=response.content or "")


class RAGSchemaExecutor:
    """Step 2 : Récupère le contexte schéma via RAG."""
    def __call__(self, step_input: StepInput) -> StepOutput:
        response = rag_schema_agent.run(step_input.previous_step_content)
        return StepOutput(content=response.content or "")


class SQLGeneratorExecutor:
    """Step 3 : Génère le SQL avec instructions dynamiques (RBAC)."""
    def __init__(self, state: PipelineState):
        self.state = state

    def __call__(self, step_input: StepInput) -> StepOutput:
        agent = Agent(
            name="SQL Generator",
            model=get_model(),
            description="Génère une requête SQL PostgreSQL.",
            instructions=build_sql_generator_instructions(self.state.allowed_tables),
            markdown=True,
        )
        response = agent.run(step_input.previous_step_content)
        self.state.sql_query = extract_sql(response.content or "")
        return StepOutput(content=response.content or "")


class SQLSecurityExecutor:
    """Step 4 : Valide la sécurité SQL + hard check regex. Stoppe le pipeline si rejeté."""
    def __init__(self, state: PipelineState):
        self.state = state

    def __call__(self, step_input: StepInput) -> StepOutput:
        agent = Agent(
            name="SQL Security Agent",
            model=get_model(),
            description="Valide la sécurité de la requête SQL générée.",
            instructions=build_sql_security_instructions(self.state.allowed_tables),
            markdown=True,
        )
        response = agent.run(step_input.previous_step_content)
        security_text = response.content or ""

        # Agent-level rejection
        if "REJETÉE" in security_text.upper() or "REJETEE" in security_text.upper():
            self.state.sql_query = None
            return StepOutput(
                content=f"Requête SQL rejetée pour raison de sécurité : {security_text}",
                success=False,
            )

        # Hard check regex (defense in depth)
        if self.state.sql_query:
            referenced = extract_table_names(self.state.sql_query)
            unauthorized = referenced - set(self.state.allowed_tables)
            if unauthorized:
                self.state.sql_query = None
                return StepOutput(
                    content=f"Accès refusé : vous n'avez pas la permission d'interroger les tables : {', '.join(sorted(unauthorized))}.",
                    success=False,
                )

        return StepOutput(content=security_text)


class DBExecutorExecutor:
    """Step 5 : Exécute le SQL validé en base de données."""
    def __call__(self, step_input: StepInput) -> StepOutput:
        response = db_executor_agent.run(step_input.previous_step_content)
        return StepOutput(content=response.content or "")


class ResponseFormatterExecutor:
    """Step 6 : Formate la réponse finale en langage naturel."""
    def __init__(self, state: PipelineState):
        self.state = state

    def __call__(self, step_input: StepInput) -> StepOutput:
        response = response_formatter_agent.run(
            step_input.previous_step_content, session_id=self.state.session_id
        )
        return StepOutput(content=response.content or "")


# ══════════════════════════════════════════════════════════════════════════════
# WORKFLOW PIPELINE
# ══════════════════════════════════════════════════════════════════════════════


def run_pipeline(question: str, session_id: str | None = None, allowed_tables: list[str] | None = None) -> dict:
    """Exécute le pipeline Text-to-SQL via un Workflow Agno avec filtrage RBAC."""
    if allowed_tables is None:
        allowed_tables = list(ALL_TABLES)

    state = PipelineState(allowed_tables, session_id)

    pipeline = Workflow(
        name="Text-to-SQL RBAC Pipeline",
        steps=[
            Step(name="Intent Analysis", executor=IntentExecutor(state)),
            Step(name="RAG Schema Retrieval", executor=RAGSchemaExecutor()),
            Step(name="SQL Generation", executor=SQLGeneratorExecutor(state)),
            Step(name="SQL Security", executor=SQLSecurityExecutor(state)),
            Step(name="DB Execution", executor=DBExecutorExecutor()),
            Step(name="Response Formatting", executor=ResponseFormatterExecutor(state)),
        ],
    )

    result = pipeline.run(input=question)
    content = result.content if hasattr(result, "content") else str(result)

    return {
        "response": content or "Désolé, je n'ai pas pu traiter votre question.",
        "sql_query": state.sql_query,
    }

