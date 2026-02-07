"""
Skill 03 : Knowledge / RAG
============================
Concept Agno : Les Knowledge Bases donnent aux agents accès à des informations
au-delà de leurs données d'entraînement via le Retrieval-Augmented Generation (RAG).

Processus : Ingestion → Chunking & Embedding → Recherche & Récupération

Documentation : https://docs.agno.com/knowledge/overview
"""

from agno.agent import Agent
from agno.knowledge.knowledge import Knowledge
from agno.models.openai import OpenAIChat


# ── 1. Knowledge avec ChromaDB (vectorielle locale) ──────────────────────────
# from agno.vectordb.chroma import ChromaDb
#
# knowledge_chroma = Knowledge(
#     vector_db=ChromaDb(collection="docs", path="tmp/chromadb"),
# )
#
# # Ingérer du contenu depuis une URL
# knowledge_chroma.insert(url="https://docs.agno.com/introduction.md")
#
# agent_rag_chroma = Agent(
#     model=OpenAIChat(id="gpt-4o"),
#     knowledge=knowledge_chroma,
#     search_knowledge=True,  # Active la recherche automatique
#     instructions="Tu réponds en te basant sur la knowledge base. Réponds en français.",
#     markdown=True,
# )


# ── 2. Knowledge avec LanceDB ────────────────────────────────────────────────
# from agno.vectordb.lancedb import LanceDb
#
# knowledge_lance = Knowledge(
#     vector_db=LanceDb(table_name="documents", uri="tmp/lancedb"),
# )


# ── 3. Knowledge avec PgVector (PostgreSQL) ──────────────────────────────────
# from agno.vectordb.pgvector import PgVector
#
# knowledge_pg = Knowledge(
#     vector_db=PgVector(
#         table_name="documents",
#         db_url="postgresql://user:password@localhost:5432/mydb",
#     ),
# )


# ── 4. Agentic RAG vs Traditional RAG ────────────────────────────────────────
# Agentic RAG (défaut) : L'agent décide QUAND chercher
# Traditional RAG      : Le contexte est TOUJOURS injecté

# Agent avec Agentic RAG (search_knowledge=True)
# → L'agent utilise un outil de recherche et décide quand l'appeler

# Agent avec Traditional RAG (always_include_knowledge=True)  [NON RECOMMANDÉ]
# → Le contexte est toujours injecté, même si pas nécessaire


# ── 5. Knowledge dynamique (l'agent peut apprendre) ──────────────────────────
# def save_learning(title: str, insight: str) -> str:
#     """Sauvegarder un insight découvert par l'agent.
#
#     Args:
#         title (str): Titre de l'insight.
#         insight (str): Contenu de l'insight.
#     """
#     knowledge_chroma.insert(name=title, text_content=insight)
#     return f"Insight sauvegardé : {title}"
#
# agent_learner = Agent(
#     model=OpenAIChat(id="gpt-4o"),
#     knowledge=knowledge_chroma,
#     search_knowledge=True,
#     tools=[save_learning],
#     instructions="Tu peux sauvegarder des insights dans ta base de connaissances.",
#     markdown=True,
# )


# ── 6. Exemple fonctionnel minimal ───────────────────────────────────────────
# Pour un exemple fonctionnel complet, décommenter et installer :
# pip install agno chromadb

if __name__ == "__main__":
    print("=" * 60)
    print("Skill 03 : Knowledge / RAG")
    print("=" * 60)
    print()
    print("Ce skill démontre les concepts de Knowledge Base dans Agno.")
    print()
    print("Types de Vector DB supportés :")
    print("  - ChromaDB (local)")
    print("  - LanceDB (local)")
    print("  - PgVector (PostgreSQL)")
    print("  - Pinecone (cloud)")
    print("  - Qdrant (cloud)")
    print("  - Weaviate (cloud)")
    print("  - ... et 20+ autres")
    print()
    print("Modes RAG :")
    print("  - Agentic RAG : l'agent décide quand chercher")
    print("  - Traditional RAG : contexte toujours injecté")
    print()
    print("Pour exécuter : décommentez le code et configurez votre vector DB.")
