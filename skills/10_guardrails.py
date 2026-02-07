"""
Skill 10 : Guardrails (Garde-fous)
=====================================
Concept Agno : Les guardrails sont des hooks de pré-traitement qui s'exécutent
avant qu'un agent ne traite l'entrée. Ils permettent la validation,
la détection de PII, la défense contre l'injection de prompt, etc.

Documentation : https://docs.agno.com/guardrails/overview
"""

import re

from agno.agent import Agent
from agno.exceptions import CheckTrigger, InputCheckError
from agno.models.openai import OpenAIChat
from agno.run.agent import RunInput


# ── 1. Guardrail custom : Détection d'URL ────────────────────────────────────
class URLGuardrail:
    """Guardrail qui bloque les entrées contenant des URLs."""

    def check(self, run_input: RunInput) -> None:
        """Vérifie que l'entrée ne contient pas d'URLs."""
        if isinstance(run_input.input_content, str):
            url_pattern = r"https?://[^\s]+|www\.[^\s]+"
            if re.search(url_pattern, run_input.input_content):
                raise InputCheckError(
                    "L'entrée contient des URLs, ce qui n'est pas autorisé.",
                    check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
                )

    async def async_check(self, run_input: RunInput) -> None:
        """Version async pour .arun()."""
        self.check(run_input)


# ── 2. Guardrail custom : Détection d'opérations SQL dangereuses ─────────────
class SQLInjectionGuardrail:
    """Guardrail qui bloque les tentatives d'injection SQL."""

    DANGEROUS_KEYWORDS = [
        "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
        "EXEC", "EXECUTE", "CREATE", "GRANT", "REVOKE",
    ]

    def check(self, run_input: RunInput) -> None:
        """Vérifie que l'entrée ne contient pas d'opérations SQL dangereuses."""
        if isinstance(run_input.input_content, str):
            content_upper = run_input.input_content.upper()
            for keyword in self.DANGEROUS_KEYWORDS:
                if keyword in content_upper:
                    raise InputCheckError(
                        f"Opération SQL dangereuse détectée : '{keyword}'. "
                        "Seules les requêtes SELECT sont autorisées.",
                        check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
                    )

    async def async_check(self, run_input: RunInput) -> None:
        self.check(run_input)


# ── 3. Guardrail custom : Validation de longueur ─────────────────────────────
def validate_input_length(run_input: RunInput) -> None:
    """Pre-hook pour valider la longueur de l'entrée."""
    max_length = 1000
    if isinstance(run_input.input_content, str):
        if len(run_input.input_content) > max_length:
            raise InputCheckError(
                f"Entrée trop longue ({len(run_input.input_content)} chars). "
                f"Maximum autorisé : {max_length} caractères.",
                check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
            )


# ── 4. Guardrails intégrés Agno ──────────────────────────────────────────────
# from agno.guardrails import PIIDetectionGuardrail
# from agno.guardrails import PromptInjectionGuardrail
# from agno.guardrails import OpenAIModerationGuardrail


# ── 5. Agent avec guardrails ─────────────────────────────────────────────────
agent_secured = Agent(
    name="Secured SQL Agent",
    model=OpenAIChat(id="gpt-4o"),
    pre_hooks=[
        validate_input_length,
        URLGuardrail(),
        SQLInjectionGuardrail(),
    ],
    instructions="Tu es un assistant Text-to-SQL sécurisé. "
                 "Tu génères uniquement des requêtes SELECT. "
                 "Réponds en français.",
    markdown=True,
)


# ── 6. Exécution ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Requête normale (OK)
    print("=== Requête normale ===\n")
    try:
        agent_secured.print_response(
            "Combien de clients sont actifs ?",
            stream=True,
        )
    except InputCheckError as e:
        print(f"BLOQUÉ : {e}")

    print("\n" + "=" * 60 + "\n")

    # Injection SQL (BLOQUÉE)
    print("=== Tentative d'injection SQL ===\n")
    try:
        agent_secured.print_response(
            "SELECT * FROM clients; DROP TABLE clients;--",
            stream=True,
        )
    except InputCheckError as e:
        print(f"BLOQUÉ : {e}")

    print("\n" + "=" * 60 + "\n")

    # URL (BLOQUÉE)
    print("=== Tentative avec URL ===\n")
    try:
        agent_secured.print_response(
            "Regarde https://malicious-site.com/exploit",
            stream=True,
        )
    except InputCheckError as e:
        print(f"BLOQUÉ : {e}")
