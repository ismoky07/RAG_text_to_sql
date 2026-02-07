"""
Skill 08 : Reasoning (Raisonnement)
======================================
Concept Agno : Le raisonnement permet aux agents de "penser" avant de répondre
et d'analyser les résultats des appels d'outils.

3 approches :
1. Reasoning Models   → Modèles qui pensent nativement (GPT-5, Claude 4.5...)
2. Reasoning Tools    → Outils explicites (scratchpad) pour structurer le raisonnement
3. Reasoning Agents   → Transforme n'importe quel modèle en système de raisonnement

Documentation : https://docs.agno.com/reasoning/overview
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.reasoning import ReasoningTools


# ── 1. Reasoning Model (modèle natif de raisonnement) ────────────────────────
# Utilise un modèle qui pense nativement avant de répondre.
# Idéal pour les problèmes complexes en un seul coup.

# from agno.models.openai import OpenAIResponses
#
# agent_reasoning_model = Agent(
#     model=OpenAIResponses(id="o3-mini"),  # Modèle de raisonnement natif
# )


# ── 2. Reasoning Tools (outils de raisonnement) ──────────────────────────────
# Ajoute des outils explicites comme un scratchpad pour structurer la pensée.
# Fonctionne avec N'IMPORTE QUEL modèle.

agent_reasoning_tools = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[ReasoningTools(add_instructions=True)],
    instructions="Utilise les outils de raisonnement pour structurer ta pensée. "
                 "Utilise des tableaux quand c'est possible. "
                 "Réponds en français.",
    markdown=True,
)


# ── 3. Reasoning Agent (raisonnement par prompting) ──────────────────────────
# Active le raisonnement step-by-step via l'ingénierie de prompt.
# Fonctionne avec N'IMPORTE QUEL modèle.

agent_reasoning = Agent(
    model=OpenAIChat(id="gpt-4o"),
    reasoning=True,  # Active le chain-of-thought
    instructions="Réponds en français.",
    markdown=True,
)


# ── 4. Hybrid Pattern (raisonnement + réponse) ───────────────────────────────
# Combine un modèle de raisonnement (DeepSeek-R1) avec un modèle de réponse (GPT-4o).

# from agno.models.groq import Groq
#
# agent_hybrid = Agent(
#     model=OpenAIChat(id="gpt-4o"),
#     reasoning_model=Groq(
#         id="deepseek-r1-distill-llama-70b",
#         temperature=0.6,
#         max_tokens=1024,
#         top_p=0.95,
#     ),
# )


# ── 5. Exécution ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Reasoning Tools ===\n")
    agent_reasoning_tools.print_response(
        "Analyse les avantages et inconvénients d'utiliser un ORM vs du SQL brut "
        "pour un projet d'analyse de données.",
        stream=True,
        show_full_reasoning=True,
    )

    print("\n" + "=" * 60 + "\n")

    print("=== Reasoning Agent ===\n")
    agent_reasoning.print_response(
        "Un e-commerce a 10 000 clients. 30% sont inactifs depuis 6 mois. "
        "Parmi les actifs, 20% sont premium. "
        "Combien de clients premium actifs y a-t-il ? "
        "Explique ton raisonnement étape par étape.",
        stream=True,
        show_full_reasoning=True,
    )
