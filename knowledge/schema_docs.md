<!--
  Documents RAG Schema
  Chaque section --- DOCUMENT --- est vectorisée séparément dans PgVector.
  Modifie ce fichier pour mettre à jour les connaissances de l'IA.
-->

--- DOCUMENT ---
type: database_overview

IMPORTANT : La base de données contient EXACTEMENT 3 tables. Il n'existe AUCUNE autre table.
Tables autorisées : clients, produits, commandes.
Il n'existe PAS de table "ventes", "details_commande", "detail_commande", "orders", "sales" ou autre.
Les ventes sont stockées dans la table "commandes".
Le chiffre d'affaires se calcule à partir de la table "commandes" (colonne montant_total).
Les détails d'une commande (quel produit, quel client) se trouvent dans la table "commandes" via les clés étrangères client_id et produit_id.

--- DOCUMENT ---
type: table_structure
table: clients

Table 'clients' : stocke les informations des clients.
Colonnes :
- id (SERIAL, clé primaire) : identifiant unique du client
- nom (VARCHAR 100) : nom de famille du client
- prenom (VARCHAR 100) : prénom du client
- email (VARCHAR 200, unique) : adresse email du client
- ville (VARCHAR 100) : ville de résidence du client
- date_inscription (DATE) : date à laquelle le client s'est inscrit
- statut (VARCHAR 20) : statut du client, valeurs possibles : 'actif' ou 'inactif'

--- DOCUMENT ---
type: table_structure
table: produits

Table 'produits' : stocke le catalogue des produits.
Colonnes :
- id (SERIAL, clé primaire) : identifiant unique du produit
- nom (VARCHAR 100) : nom du produit
- categorie (VARCHAR 50) : catégorie du produit (ex: Informatique, Téléphonie, Audio, Wearable)
- prix (DECIMAL 10,2) : prix unitaire du produit en euros

--- DOCUMENT ---
type: table_structure
table: commandes

Table 'commandes' : stocke les commandes passées par les clients.
Colonnes :
- id (SERIAL, clé primaire) : identifiant unique de la commande
- client_id (INTEGER, clé étrangère vers clients.id) : le client qui a passé la commande
- produit_id (INTEGER, clé étrangère vers produits.id) : le produit commandé
- quantite (INTEGER) : nombre d'unités commandées
- montant_total (DECIMAL 10,2) : montant total de la commande en euros
- date_commande (DATE) : date à laquelle la commande a été passée
- statut (VARCHAR 20) : statut de la commande, valeurs possibles : 'completee', 'en_cours', 'annulee'

--- DOCUMENT ---
type: relations

Relations entre les tables :
- commandes.client_id → clients.id : chaque commande est liée à un client
- commandes.produit_id → produits.id : chaque commande est liée à un produit

Pour joindre les tables :
- Clients et commandes : JOIN commandes ON commandes.client_id = clients.id
- Commandes et produits : JOIN produits ON produits.id = commandes.produit_id
- Les 3 tables : FROM commandes JOIN clients ON clients.id = commandes.client_id JOIN produits ON produits.id = commandes.produit_id

--- DOCUMENT ---
type: business_rules

Règles métier :
- Un client actif est un client dont le statut est 'actif'
- Un client inactif est un client dont le statut est 'inactif'
- Une vente réalisée est une commande dont le statut est 'completee'
- Une commande en cours a le statut 'en_cours'
- Une commande annulée a le statut 'annulee'
- Le chiffre d'affaires se calcule en sommant montant_total des commandes 'completee'
- Le panier moyen = chiffre d'affaires / nombre de commandes completees
- Les villes disponibles : Paris, Lyon, Marseille, Toulouse, Bordeaux, Lille, Nantes
- Les catégories de produits : Informatique, Téléphonie, Audio, Wearable

--- DOCUMENT ---
type: sql_examples

Exemples de requêtes SQL courantes :

1. Compter les clients actifs :
   SELECT COUNT(*) FROM clients WHERE statut = 'actif'

2. Clients par ville :
   SELECT ville, COUNT(*) AS nombre_clients FROM clients GROUP BY ville ORDER BY nombre_clients DESC

3. Chiffre d'affaires total :
   SELECT SUM(montant_total) AS chiffre_affaires FROM commandes WHERE statut = 'completee'

4. Top produits vendus :
   SELECT p.nom, COUNT(*) AS nb_ventes, SUM(co.montant_total) AS ca FROM commandes co JOIN produits p ON p.id = co.produit_id WHERE co.statut = 'completee' GROUP BY p.nom ORDER BY ca DESC

5. Commandes d'un client par nom :
   SELECT c.nom, c.prenom, p.nom AS produit, co.montant_total, co.date_commande FROM commandes co JOIN clients c ON c.id = co.client_id JOIN produits p ON p.id = co.produit_id WHERE c.nom = 'Dupont'

6. Évolution des ventes par année :
   SELECT EXTRACT(YEAR FROM date_commande) AS annee, COUNT(*) AS nb_commandes, SUM(montant_total) AS ca FROM commandes WHERE statut = 'completee' GROUP BY annee ORDER BY annee
