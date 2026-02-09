"""
Guardrails : Validation des entrées et sorties du pipeline.
=============================================================
Utilise le système natif BaseGuardrail d'Agno.
"""

import re

from agno.guardrails import BaseGuardrail
from agno.exceptions import InputCheckError, CheckTrigger
from agno.run.agent import RunInput


# ══════════════════════════════════════════════════════════════════════════════
# 1. SALUTATIONS - Détection des greetings pour réponse accueillante
# ══════════════════════════════════════════════════════════════════════════════

GREETING_PATTERNS = [
    # Salutations FR
    r"\b(bonjour|bonsoir|salut|coucou|hey|wesh|yo|salam)\b",
    # Salutations EN
    r"\b(hello|hi|hey|good morning|good evening|good afternoon)\b",
    # Remerciements / Au revoir
    r"\b(merci|au revoir|bye|goodbye|à bientôt|à plus|adieu|bonne journée|bonne soirée)\b",
    # Questions sur l'identité du bot
    r"\b(qui es-tu|tu es qui|what are you|comment tu t'appelles|tu fais quoi|c'est quoi)\b",
    r"\b(quel est ton (nom|rôle)|présente-toi|tu sers à quoi)\b",
    # Demande d'aide
    r"\b(aide|help|comment ça marche|comment utiliser|tu peux m'aider)\b",
    r"\b(que (peux|sais)-tu faire|tes capacités|tes fonctionnalités)\b",
]

GREETING_RESPONSE = (
    "Bonjour ! Je suis votre **AI Data Assistant**.\n\n"
    "Mon rôle est de répondre à vos questions sur les données de l'entreprise "
    "(clients, produits, commandes) en les transformant en requêtes SQL.\n\n"
    "Voici quelques exemples de questions que vous pouvez me poser :\n"
    "- Combien de clients actifs sont dans chaque ville ?\n"
    "- Quel est le chiffre d'affaires total ?\n"
    "- Quels sont les 5 produits les plus vendus ?\n"
    "- Quelles sont les commandes de Marie Dupont ?\n\n"
    "Comment puis-je vous aider ?"
)


# ══════════════════════════════════════════════════════════════════════════════
# 2. HORS-SUJET - Bloque les questions qui ne concernent pas les données métier
# ══════════════════════════════════════════════════════════════════════════════

OFF_TOPIC_PATTERNS = [
    # ── Météo ──
    r"\b(météo|weather|température|pluie|soleil|neige|vent|orage|nuage|tempête)\b",
    r"\b(brouillard|grêle|canicule|verglas|climat|prévision|forecast)\b",
    r"(temps qu.il fait|quel temps|il fait .* temps|il fait (beau|chaud|froid|moche))",
    # ── Humour / Blagues ──
    r"\b(blague|joke|humour|drôle|funny|raconte|rigolo|marrant|gag|sketch)\b",
    r"\b(devinette|charade|poème|poésie|rime)\b",
    # ── Cuisine / Nourriture ──
    r"\b(recette|cuisine|cuisson|ingrédient|manger|plat|restaurant|menu|repas)\b",
    r"\b(dîner|déjeuner|petit-déjeuner|gâteau|dessert|pâtisserie|boulangerie)\b",
    r"\b(végétarien|végan|régime|calorie|nutrition)\b",
    # ── Programmation / Code ──
    r"\b(python|javascript|java|html|css|typescript|react|angular|vue)\b",
    r"\b(programmer|coder|développer|framework|library|api|github|gitlab)\b",
    r"\b(algorithme|variable|fonction|boucle|compiler|debug|bug|stack)\b",
    r"\b(php|ruby|rust|golang|swift|kotlin|flutter|django|nodejs)\b",
    # ── Politique ──
    r"\b(politique|élection|président|parti|gouvernement|ministre|député)\b",
    r"\b(sénat|parlement|vote|référendum|loi|constitution|campagne)\b",
    r"\b(gauche|droite|macron|trump|biden|démocratie|dictature)\b",
    # ── Sport ──
    r"\b(sport|football|tennis|basket|rugby|natation|athlétisme|volleyball)\b",
    r"\b(olympique|coupe du monde|championnat|ligue|fifa|uefa|nba)\b",
    r"\b(but|score|équipe|joueur|entraîneur|arbitre|stade|marathon)\b",
    r"\b(handball|golf|ski|surf|boxe|karaté|judo|escrime|cyclisme)\b",
    # ── Divertissement / Médias ──
    r"\b(film|série|musique|chanson|acteur|actrice|cinéma|netflix|disney)\b",
    r"\b(youtube|spotify|streaming|concert|album|artiste|réalisateur)\b",
    r"\b(oscar|grammy|jeu vidéo|gaming|playstation|xbox|nintendo|manga|anime)\b",
    r"\b(roman|livre|auteur|écrivain|bibliothèque|lecture|bande dessinée)\b",
    # ── Voyage / Tourisme ──
    r"\b(voyag|vacance|hôtel|avion|train|destination|tourisme|croisière)\b",
    r"\b(plage|montagne|camping|visa|passeport|billet|valise|aéroport)\b",
    r"\b(airbnb|booking|excursion|itinéraire|road trip)\b",
    # ── Santé / Médecine ──
    r"\b(santé|médecin|maladie|symptôme|docteur|hôpital|pharmacie)\b",
    r"\b(médicament|ordonnance|douleur|fièvre|grippe|covid|vaccin|virus)\b",
    r"\b(chirurgie|opération|dentiste|kiné|psychologue|thérapie|allergie)\b",
    # ── Animaux ──
    r"\b(animal|animaux|chien|chat|oiseau|poisson|hamster|lapin|tortue)\b",
    r"\b(vétérinaire|cheval|serpent|araignée|insecte|zoo|aquarium)\b",
    # ── Éducation ──
    r"\b(école|université|examen|cours|diplôme|étudiant|professeur)\b",
    r"\b(baccalauréat|licence|master|doctorat|thèse|scolaire|bourse)\b",
    # ── Religion / Spiritualité ──
    r"\b(religion|dieu|église|mosquée|synagogue|temple|prière|bible|coran)\b",
    r"\b(foi|spirituel|croyance|athée|bouddhisme|islam|christianisme)\b",
    # ── Relations / Sentiments ──
    r"\b(amour|couple|mariage|divorce|rencontre|relation|sentiment)\b",
    r"\b(cœur|jalousie|rupture|fiancé|célibataire|tinder|dating)\b",
    # ── Mode / Shopping ──
    r"\b(mode|vêtement|chaussure|robe|pantalon|marque|tendance|shopping)\b",
    r"\b(bijou|accessoire|parfum|maquillage|coiffure|beauté|cosmétique)\b",
    # ── Astrologie / Ésotérisme ──
    r"\b(horoscope|astrologie|signe|zodiaque|verseau|balance|scorpion)\b",
    r"\b(tarot|voyance|médium|ésotéri|paranormal|fantôme|ovni)\b",
    # ── Culture générale / Géographie ──
    r"\b(capitale|population|superficie|continent|océan|fleuve|montagne)\b",
    r"\b(roi|reine|empereur|guerre|bataille|révolution|siècle|histoire)\b",
    # ── Sciences ──
    r"\b(mathématique|physique|chimie|biologie|formule|équation|atome)\b",
    r"\b(molécule|espace|planète|galaxie|étoile|solaire|gravité|quantique)\b",
    r"\b(dinosaure|fossile|évolution|darwin|adn|génétique|cellule)\b",
    # ── Immobilier / Logement ──
    r"\b(immobilier|appartement|maison|loyer|achat|vente|hypothèque)\b",
    r"\b(déménagement|propriétaire|locataire|agence immobilière)\b",
    # ── Automobile / Transport ──
    r"\b(voiture|automobile|moto|vélo|permis de conduire|essence|diesel)\b",
    r"\b(tesla|bmw|mercedes|peugeot|renault|pneu|garage|mécanicien)\b",
    # ── Actualité / Médias ──
    r"\b(actualité|nouvelles|journal|infos|presse|média|reporter|journaliste)\b",
    # ── Finance personnelle ──
    r"\b(bourse|bitcoin|crypto|action|investir|épargne|placement|trading)\b",
    r"\b(impôt|taxe|retraite|assurance|banque|crédit|prêt|hypothèque)\b",
    # ── Bricolage / Jardinage ──
    r"\b(bricolage|jardinage|plante|fleur|arbre|pelouse|potager|outil)\b",
    r"\b(peinture|plomberie|électricité|carrelage|rénovation|menuiserie)\b",
    # ── Technologie grand public ──
    r"\b(smartphone|iphone|samsung|android|ios|tablette|gadget)\b",
    r"\b(wifi|bluetooth|5g|fibre|internet|réseau social|facebook|instagram|tiktok)\b",
]

OFF_TOPIC_RESPONSE = (
    "Désolé, je ne suis pas en mesure de répondre à ce type de question. "
    "Mon domaine se limite aux **données de l'entreprise** : clients, produits et commandes.\n\n"
    "Essayez par exemple :\n"
    "- Quel est le chiffre d'affaires total ?\n"
    "- Combien de clients actifs par ville ?\n"
    "- Quels sont les produits les plus vendus ?"
)


# ══════════════════════════════════════════════════════════════════════════════
# 3. SQL INJECTION + ACTIONS DESTRUCTRICES
# ══════════════════════════════════════════════════════════════════════════════

SQL_INJECTION_PATTERNS = [
    # ── Commandes SQL destructrices (EN) ──
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|GRANT|REVOKE)\b",
    r"\b(CREATE|RENAME|REPLACE|MERGE|UPSERT)\b",
    r"\b(EXEC|EXECUTE|xp_|sp_)\b",
    r"\b(SHUTDOWN|KILL|BACKUP|RESTORE)\b",
    # ── Injection via commentaires / métacaractères ──
    r"(--|;|/\*|\*/|@@|#\s)",
    r"(char\(|nchar\(|varchar\(|concat\(|hex\(|unhex\()",
    r"(0x[0-9a-fA-F]+)",
    # ── UNION-based injection ──
    r"(\bUNION\b.*\bSELECT\b)",
    r"(\bUNION\b\s+\bALL\b)",
    # ── Boolean-based injection ──
    r"(\bOR\b\s+\d+\s*=\s*\d+)",
    r"(\bAND\b\s+\d+\s*=\s*\d+)",
    r"(\bOR\b\s+['\"].*['\"]\s*=\s*['\"])",
    r"(\bOR\b\s+''='')",
    r"(\bOR\b\s+true\b)",
    # ── Time-based injection ──
    r"\b(SLEEP|WAITFOR|DELAY|BENCHMARK|pg_sleep)\b",
    # ── Accès aux tables système ──
    r"\b(pg_catalog|pg_shadow|pg_roles|pg_user|pg_tables)\b",
    r"\b(information_schema|sys\.|sysobjects|syscolumns)\b",
    # ── Opérations fichiers ──
    r"\b(LOAD_FILE|INTO\s+OUTFILE|INTO\s+DUMPFILE|COPY\s+TO|COPY\s+FROM)\b",
    # ── Actions destructrices en français ──
    r"\b(supprime[rz]?|efface[rz]?|détruire?|détruis)\b",
    r"\b(vide[rz]?|purge[rz]?|nettoie[rz]?|nettoyer)\b",
    r"\b(modifie[rz]?|modifier|édite[rz]?|éditer)\b",
    r"\b(met[sz]?\s.*à jour|mise à jour|mettre à jour)\b",
    r"\b(ajoute[rz]?|ajouter|insère[rz]?|insérer)\b",
    r"\b(créer|crée[rz]?|renomme[rz]?|renommer)\b",
    r"\b(remplace[rz]?|remplacer|écrase[rz]?|écraser)\b",
    r"\b(réinitialise[rz]?|réinitialiser|reset)\b",
    r"\b(enlève[rz]?|enlever|retire[rz]?|retirer)\b",
    r"\b(restaure[rz]?|restaurer|migre[rz]?|migrer)\b",
]

DESTRUCTIVE_RESPONSE = (
    "Je ne peux pas effectuer d'opérations de modification sur la base de données. "
    "Mon rôle est uniquement de **consulter** les données (lecture seule).\n\n"
    "Essayez plutôt une question de consultation :\n"
    "- Quels sont les clients actifs ?\n"
    "- Quel est le chiffre d'affaires total ?\n"
    "- Quels sont les produits les plus vendus ?"
)


# ══════════════════════════════════════════════════════════════════════════════
# 4. PROMPT INJECTION - Tentatives de manipulation de l'IA
# ══════════════════════════════════════════════════════════════════════════════

PROMPT_INJECTION_PATTERNS = [
    # ── Ignorer les instructions (FR) ──
    r"(ignore[rz]?\s+(tes|les|mes|ces)\s+instructions)",
    r"(oublie[rz]?\s+(tes|les|mes|ces)\s+instructions)",
    r"(ne\s+(tiens?|tenez)\s+pas\s+compte)",
    r"(fais\s+comme\s+si|fais\s+semblant)",
    # ── Ignorer les instructions (EN) ──
    r"(ignore\s+(previous|all|your|the)\s+instructions?)",
    r"(forget\s+(your|all|previous)\s+instructions?)",
    r"(disregard\s+(your|all|previous))",
    # ── Changement de rôle (FR) ──
    r"(tu\s+es\s+maintenant|agis\s+comme|joue\s+le\s+rôle)",
    r"(comporte[- ]toi\s+comme|deviens|transforme[- ]toi)",
    r"(ton\s+nouveau\s+rôle|ta\s+nouvelle\s+mission)",
    # ── Changement de rôle (EN) ──
    r"(you\s+are\s+now|act\s+as|pretend\s+(you are|to be))",
    r"(your\s+new\s+role|your\s+new\s+purpose)",
    r"(roleplay|role[- ]play)",
    # ── Jailbreak / Bypass ──
    r"\b(jailbreak|bypass|contourne[rz]?|hack|exploit)\b",
    r"\b(DAN|do anything now)\b",
    r"(developer\s+mode|mode\s+développeur|god\s+mode|admin\s+mode)",
    r"(no\s+restrictions?|sans\s+restrictions?|sans\s+limites?)",
    r"(no\s+rules?|sans\s+règles?)",
    r"(unrestricted|unfiltered|uncensored)",
    # ── Accès au prompt système ──
    r"(system\s+prompt|prompt\s+système|instructions?\s+système)",
    r"(montre[rz]?\s+(tes|les)\s+(instructions|règles|consignes))",
    r"(affiche[rz]?\s+(ton|le)\s+prompt)",
    r"(répète[rz]?\s+(tes|les)\s+instructions)",
    r"(show\s+(me\s+)?(your|the)\s+(prompt|instructions|rules))",
    r"(reveal\s+(your|the)\s+(prompt|instructions|system))",
    # ── Injection via formatage ──
    r"(\[SYSTEM\]|\[INST\]|\[/INST\]|<<SYS>>|<\|im_start\|>)",
    r"(###\s*(System|Human|Assistant|Instruction))",
    # ── Override / Outrepasser ──
    r"\b(override|outrepasse[rz]?|surcharge[rz]?|dépasse[rz]?)\b",
    r"(priorité\s+maximale|highest\s+priority|urgent\s+override)",
]

PROMPT_INJECTION_RESPONSE = (
    "Tentative de manipulation détectée. Je ne peux pas modifier mon comportement.\n\n"
    "Je suis un **assistant data** dédié aux questions sur les données de l'entreprise.\n\n"
    "Essayez par exemple :\n"
    "- Quel est le chiffre d'affaires total ?\n"
    "- Combien de clients actifs par ville ?\n"
    "- Quels sont les produits les plus vendus ?"
)


# ══════════════════════════════════════════════════════════════════════════════
# FONCTIONS DE VÉRIFICATION (utilisées au niveau API)
# ══════════════════════════════════════════════════════════════════════════════

def is_greeting(text: str) -> bool:
    """Vérifie si le texte est une salutation ou demande d'aide."""
    text_lower = text.lower()
    for pattern in GREETING_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def is_off_topic(text: str) -> bool:
    """Vérifie si le texte est une question hors-sujet."""
    text_lower = text.lower()
    for pattern in OFF_TOPIC_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def is_destructive(text: str) -> bool:
    """Vérifie si le texte contient une intention destructrice (SQL injection ou action FR)."""
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def is_prompt_injection(text: str) -> bool:
    """Vérifie si le texte tente de manipuler l'IA (prompt injection)."""
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
# GUARDRAIL CLASSES (utilisées en pre_hooks sur les agents Agno)
# ══════════════════════════════════════════════════════════════════════════════

class TopicGuardrail(BaseGuardrail):
    """Bloque les questions qui ne concernent pas les données métier."""

    def check(self, run_input: RunInput) -> None:
        if isinstance(run_input.input_content, str):
            text = run_input.input_content.lower()
            for pattern in OFF_TOPIC_PATTERNS:
                if re.search(pattern, text):
                    raise InputCheckError(
                        OFF_TOPIC_RESPONSE,
                        check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
                    )

    async def async_check(self, run_input: RunInput) -> None:
        self.check(run_input)


class SQLInjectionGuardrail(BaseGuardrail):
    """Détecte les tentatives d'injection SQL et actions destructrices."""

    def check(self, run_input: RunInput) -> None:
        if isinstance(run_input.input_content, str):
            text = run_input.input_content
            for pattern in SQL_INJECTION_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    raise InputCheckError(
                        DESTRUCTIVE_RESPONSE,
                        check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
                    )

    async def async_check(self, run_input: RunInput) -> None:
        self.check(run_input)


class PromptInjectionGuardrail(BaseGuardrail):
    """Détecte les tentatives de manipulation de l'IA (prompt injection)."""

    def check(self, run_input: RunInput) -> None:
        if isinstance(run_input.input_content, str):
            text = run_input.input_content
            for pattern in PROMPT_INJECTION_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    raise InputCheckError(
                        PROMPT_INJECTION_RESPONSE,
                        check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
                    )

    async def async_check(self, run_input: RunInput) -> None:
        self.check(run_input)


class OutputSafetyGuardrail(BaseGuardrail):
    """Masque les emails et données sensibles dans la réponse."""

    def check(self, run_input: RunInput) -> None:
        if isinstance(run_input.input_content, str):
            # Masquer les emails
            run_input.input_content = EMAIL_PATTERN.sub("***@***.com", run_input.input_content)
            # Masquer les numéros de téléphone
            run_input.input_content = PHONE_PATTERN.sub("** ** ** ** **", run_input.input_content)

    async def async_check(self, run_input: RunInput) -> None:
        self.check(run_input)


# Patterns pour données sensibles en sortie
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"\b0[1-9][\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}\b")
