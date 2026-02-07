"""
Skill 02 : Tools (Outils)
===========================
Concept Agno : Les outils sont des fonctions que les agents appellent
pour interagir avec des systèmes externes (APIs, bases de données, web...).

Agno fournit 120+ toolkits pré-construits + support pour les outils custom.

Documentation : https://docs.agno.com/tools/overview
"""

import random

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools import tool
from agno.run import RunContext


# ── 1. Outil custom simple (avec décorateur @tool) ───────────────────────────
@tool
def get_weather(city: str) -> str:
    """Obtenir la météo d'une ville.

    Args:
        city (str): La ville pour laquelle obtenir la météo.
    """
    conditions = ["ensoleillé", "nuageux", "pluvieux", "neigeux", "venteux"]
    temp = random.randint(-5, 35)
    return f"La météo à {city} : {random.choice(conditions)}, {temp}°C"


@tool
def calculate_revenue(price: float, quantity: int) -> str:
    """Calculer le chiffre d'affaires.

    Args:
        price (float): Le prix unitaire du produit.
        quantity (int): La quantité vendue.
    """
    revenue = price * quantity
    return f"Chiffre d'affaires : {revenue:.2f} €"


# ── 2. Agent avec outils custom ──────────────────────────────────────────────
agent_custom_tools = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[get_weather, calculate_revenue],
    instructions="Tu es un assistant polyvalent. Utilise les outils disponibles. "
                 "Réponds en français.",
    markdown=True,
)


# ── 3. Outil avec RunContext (état persistant) ────────────────────────────────
def add_to_cart(run_context: RunContext, product: str, price: float) -> str:
    """Ajouter un produit au panier.

    Args:
        product (str): Le nom du produit.
        price (float): Le prix du produit.
    """
    cart = run_context.session_state.get("cart", [])
    cart.append({"product": product, "price": price})
    run_context.session_state["cart"] = cart
    total = sum(item["price"] for item in cart)
    return f"Ajouté : {product} ({price}€). Total panier : {total:.2f}€"


def view_cart(run_context: RunContext) -> str:
    """Afficher le contenu du panier."""
    cart = run_context.session_state.get("cart", [])
    if not cart:
        return "Le panier est vide."
    items = "\n".join(f"- {item['product']}: {item['price']}€" for item in cart)
    total = sum(item["price"] for item in cart)
    return f"Panier :\n{items}\nTotal : {total:.2f}€"


agent_with_state = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[add_to_cart, view_cart],
    session_state={"cart": []},
    instructions="Tu es un assistant e-commerce. "
                 "Aide l'utilisateur à gérer son panier. "
                 "Panier actuel : {cart}",
    markdown=True,
)


# ── 4. Utilisation d'un toolkit pré-construit ────────────────────────────────
# from agno.tools.hackernews import HackerNewsTools
#
# agent_hackernews = Agent(
#     model=OpenAIChat(id="gpt-4o"),
#     tools=[HackerNewsTools()],
#     instructions="Tu résumes les top stories de HackerNews en français.",
#     markdown=True,
# )


# ── 5. Exécution ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Outils custom
    agent_custom_tools.print_response(
        "Quelle est la météo à Paris ? Et calcule le CA pour 150 unités à 29.99€",
        stream=True,
    )

    print("\n" + "=" * 60 + "\n")

    # Outils avec état
    agent_with_state.print_response("Ajoute un laptop à 999€ et un clavier à 79€", stream=True)
    agent_with_state.print_response("Montre-moi mon panier", stream=True)
