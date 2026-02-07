"""
Tools : Outils appelés par les agents du pipeline.
=====================================================
"""

import json
import os

import psycopg2
from agno.tools import tool

DB_URL_PSYCOPG2 = os.getenv("DATABASE_URL_PSYCOPG2", "postgresql://postgres:postgres@localhost:5433/text_to_sql_db")

DANGEROUS_KEYWORDS = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "GRANT"]


@tool
def execute_sql_readonly(query: str) -> str:
    """Exécuter une requête SQL SELECT en lecture seule sur la base de données PostgreSQL.

    Args:
        query (str): La requête SQL SELECT à exécuter.
    """
    query_upper = query.strip().upper()

    if not query_upper.startswith("SELECT"):
        return "ERREUR : Seules les requêtes SELECT sont autorisées."

    for keyword in DANGEROUS_KEYWORDS:
        if keyword in query_upper:
            return f"ERREUR : Opération '{keyword}' interdite. Seul SELECT est autorisé."

    try:
        conn = psycopg2.connect(DB_URL_PSYCOPG2)
        conn.set_session(readonly=True)
        cur = conn.cursor()
        cur.execute(query)

        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

        cur.close()
        conn.close()

        if not rows:
            return "Aucun résultat trouvé."

        result = {
            "columns": columns,
            "rows": [list(row) for row in rows],
            "row_count": len(rows),
        }
        return json.dumps(result, default=str, ensure_ascii=False)

    except Exception as e:
        return f"ERREUR SQL : {str(e)}"
