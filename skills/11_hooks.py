"""
Skill 11 : Hooks (Pre-Hooks & Post-Hooks)
============================================
Concept Agno : Les hooks permettent d'exécuter de la logique custom
avant et après les exécutions d'un agent.

- Pre-hooks  : s'exécutent AVANT le traitement (validation, preprocessing)
- Post-hooks : s'exécutent APRÈS la réponse (validation, logging, transformation)

Documentation : https://docs.agno.com/hooks/overview
"""

import json
from datetime import datetime

from agno.agent import Agent
from agno.exceptions import CheckTrigger, InputCheckError, OutputCheckError
from agno.models.openai import OpenAIChat
from agno.run.agent import RunInput, RunOutput


# ── 1. Pre-Hook : Validation d'entrée ────────────────────────────────────────
def validate_input(run_input: RunInput) -> None:
    """Pre-hook : valide que l'entrée n'est pas vide et pas trop longue."""
    content = run_input.input_content
    if isinstance(content, str):
        if len(content.strip()) == 0:
            raise InputCheckError(
                "L'entrée est vide.",
                check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
            )
        if len(content) > 2000:
            raise InputCheckError(
                "L'entrée dépasse 2000 caractères.",
                check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
            )


# ── 2. Pre-Hook : Logging d'entrée ───────────────────────────────────────────
def log_input(run_input: RunInput) -> None:
    """Pre-hook : enregistre chaque requête dans un fichier de log."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "input": str(run_input.input_content)[:200],  # Tronquer pour le log
        "type": "input",
    }
    print(f"[LOG INPUT] {json.dumps(log_entry, ensure_ascii=False)}")


# ── 3. Pre-Hook : Enrichissement de l'entrée ─────────────────────────────────
def enrich_input(run_input: RunInput) -> None:
    """Pre-hook : ajoute le contexte temporel à l'entrée."""
    if isinstance(run_input.input_content, str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        run_input.input_content = (
            f"[Date actuelle : {now}] {run_input.input_content}"
        )


# ── 4. Post-Hook : Validation de sortie ──────────────────────────────────────
def validate_output_length(run_output: RunOutput) -> None:
    """Post-hook : vérifie que la réponse ne dépasse pas une taille max."""
    if run_output.content and len(run_output.content) > 5000:
        raise OutputCheckError(
            "La réponse est trop longue (> 5000 chars).",
            check_trigger=CheckTrigger.OUTPUT_NOT_ALLOWED,
        )


# ── 5. Post-Hook : Logging de sortie ─────────────────────────────────────────
def log_output(run_output: RunOutput) -> None:
    """Post-hook : enregistre chaque réponse."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "output_length": len(run_output.content) if run_output.content else 0,
        "type": "output",
    }
    print(f"[LOG OUTPUT] {json.dumps(log_entry, ensure_ascii=False)}")


# ── 6. Post-Hook : Filtrage de contenu sensible ──────────────────────────────
def redact_sensitive_data(run_output: RunOutput) -> None:
    """Post-hook : masque les données sensibles dans la réponse."""
    import re

    if run_output.content:
        # Masquer les emails
        run_output.content = re.sub(
            r"[\w.-]+@[\w.-]+\.\w+",
            "[EMAIL MASQUÉ]",
            run_output.content,
        )
        # Masquer les numéros de téléphone
        run_output.content = re.sub(
            r"\b\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}\b",
            "[TEL MASQUÉ]",
            run_output.content,
        )


# ── 7. Agent avec hooks complets ─────────────────────────────────────────────
agent_with_hooks = Agent(
    name="Monitored Agent",
    model=OpenAIChat(id="gpt-4o"),
    pre_hooks=[validate_input, log_input, enrich_input],
    post_hooks=[validate_output_length, log_output, redact_sensitive_data],
    instructions="Tu es un assistant data. Réponds en français.",
    markdown=True,
)


# ── 8. Exécution ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Agent avec Pre & Post Hooks ===\n")

    # Requête normale
    agent_with_hooks.print_response(
        "Liste-moi 3 bonnes pratiques pour sécuriser une base de données PostgreSQL.",
        stream=True,
    )

    print("\n" + "=" * 60 + "\n")

    # Requête vide (bloquée par pre-hook)
    print("=== Test entrée vide ===\n")
    try:
        agent_with_hooks.print_response("   ", stream=True)
    except InputCheckError as e:
        print(f"BLOQUÉ par pre-hook : {e}")
