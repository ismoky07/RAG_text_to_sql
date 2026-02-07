"""
Skill 14 : Evals (Évaluations)
=================================
Concept Agno : Les Evals mesurent la qualité des agents et teams.
Agno fournit 3 dimensions d'évaluation :

1. Accuracy  → Exactitude des réponses (LLM-as-a-judge)
2. Performance → Métriques opérationnelles (latence, mémoire)
3. Reliability → Qualité d'intégration des outils, gestion d'erreurs

Documentation : https://docs.agno.com/evals/overview
"""

from agno.agent import Agent
from agno.eval.accuracy import AccuracyEval, AccuracyResult
from agno.models.openai import OpenAIChat
from agno.tools import tool


# ── 1. Outil de test ─────────────────────────────────────────────────────────
@tool
def calculate(expression: str) -> str:
    """Calculer une expression mathématique.

    Args:
        expression (str): L'expression à calculer (ex: "10 * 5").
    """
    try:
        result = eval(expression)  # Simplifié pour la démo
        return str(result)
    except Exception as e:
        return f"Erreur : {e}"


@tool
def count_clients_by_city(city: str) -> str:
    """Compter les clients par ville (données simulées).

    Args:
        city (str): La ville à rechercher.
    """
    fake_data = {"Paris": 1250, "Lyon": 830, "Marseille": 645}
    count = fake_data.get(city, 0)
    return f"{count} clients à {city}"


# ── 2. Agent à tester ────────────────────────────────────────────────────────
agent_to_test = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[calculate, count_clients_by_city],
    instructions="Tu es un assistant data. "
                 "Utilise les outils pour répondre précisément. "
                 "Réponds en français.",
)


# ── 3. Eval d'Accuracy (exactitude) ──────────────────────────────────────────
def run_accuracy_evals():
    """Exécuter les tests d'exactitude."""
    test_cases = [
        {
            "input": "Calcule 10 * 5 puis élève au carré",
            "expected": "2500",
            "guidelines": "Le résultat doit contenir le nombre 2500.",
        },
        {
            "input": "Combien de clients à Paris ?",
            "expected": "1250",
            "guidelines": "Le résultat doit mentionner 1250 clients.",
        },
        {
            "input": "Combien de clients à Lyon ?",
            "expected": "830",
            "guidelines": "Le résultat doit mentionner 830 clients.",
        },
    ]

    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test {i}/{len(test_cases)} ---")
        print(f"Input    : {test['input']}")
        print(f"Expected : {test['expected']}")

        evaluation = AccuracyEval(
            model=OpenAIChat(id="gpt-4o"),
            agent=agent_to_test,
            input=test["input"],
            expected_output=test["expected"],
            additional_guidelines=test["guidelines"],
        )

        result: AccuracyResult | None = evaluation.run(print_results=True)
        results.append(result)

    # Résumé
    print("\n" + "=" * 60)
    print("RÉSUMÉ DES ÉVALUATIONS")
    print("=" * 60)
    passed = sum(1 for r in results if r and r.passed)
    print(f"Réussis : {passed}/{len(results)}")

    return results


# ── 4. Eval manuelle de Performance ──────────────────────────────────────────
import time


def run_performance_eval(question: str, max_latency_seconds: float = 10.0):
    """Évaluer la performance (latence) d'un agent."""
    print(f"\nQuestion : {question}")
    print(f"Latence max autorisée : {max_latency_seconds}s")

    start = time.time()
    response = agent_to_test.run(question)
    elapsed = time.time() - start

    print(f"Latence mesurée : {elapsed:.2f}s")
    print(f"Longueur réponse : {len(response.content)} chars")

    if elapsed <= max_latency_seconds:
        print("PERFORMANCE : OK")
    else:
        print(f"PERFORMANCE : TROP LENT ({elapsed:.2f}s > {max_latency_seconds}s)")

    return {
        "latency": elapsed,
        "response_length": len(response.content),
        "passed": elapsed <= max_latency_seconds,
    }


# ── 5. Eval manuelle de Reliability (fiabilité) ──────────────────────────────
def run_reliability_eval():
    """Évaluer la fiabilité : l'agent utilise-t-il les bons outils ?"""
    test_cases = [
        {
            "input": "Calcule 7 * 8",
            "expected_tool": "calculate",
        },
        {
            "input": "Combien de clients à Marseille ?",
            "expected_tool": "count_clients_by_city",
        },
    ]

    for test in test_cases:
        print(f"\nInput : {test['input']}")
        response = agent_to_test.run(test["input"])

        # Vérifier les outils appelés
        tools_called = []
        if hasattr(response, "messages"):
            for msg in response.messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tools_called.append(tc.function.name)

        print(f"Outils appelés : {tools_called}")
        if test["expected_tool"] in tools_called:
            print("RELIABILITY : OK")
        else:
            print(f"RELIABILITY : ÉCHEC (attendu: {test['expected_tool']})")


# ── 6. Exécution ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("=== Accuracy Evals ===")
    print("=" * 60)
    run_accuracy_evals()

    print("\n" + "=" * 60)
    print("=== Performance Eval ===")
    print("=" * 60)
    run_performance_eval("Combien de clients à Paris ?", max_latency_seconds=10.0)

    print("\n" + "=" * 60)
    print("=== Reliability Eval ===")
    print("=" * 60)
    run_reliability_eval()
