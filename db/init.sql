-- ============================================
-- Script d'initialisation de la base de données
-- Exécuté automatiquement au premier lancement Docker
-- ============================================

-- Active l'extension pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- TABLES DE DONNÉES (interrogées par le SQL généré)
-- ============================================

CREATE TABLE produits (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    categorie VARCHAR(50) NOT NULL,
    prix DECIMAL(10,2) NOT NULL
);

CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    email VARCHAR(200) UNIQUE NOT NULL,
    ville VARCHAR(100) NOT NULL,
    date_inscription DATE NOT NULL DEFAULT CURRENT_DATE,
    statut VARCHAR(20) NOT NULL DEFAULT 'actif'
);

CREATE TABLE commandes (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    produit_id INTEGER NOT NULL REFERENCES produits(id),
    quantite INTEGER NOT NULL,
    montant_total DECIMAL(10,2) NOT NULL,
    date_commande DATE NOT NULL DEFAULT CURRENT_DATE,
    statut VARCHAR(20) NOT NULL DEFAULT 'completee'
);

-- ============================================
-- DONNÉES DE TEST
-- ============================================

INSERT INTO produits (nom, categorie, prix) VALUES
('Laptop Pro 15', 'Informatique', 1299.99),
('Smartphone X12', 'Téléphonie', 899.99),
('Casque Audio BT', 'Audio', 149.99),
('Clavier Mécanique', 'Informatique', 89.99),
('Écran 27 pouces', 'Informatique', 349.99),
('Tablette Air', 'Informatique', 599.99),
('Souris Sans Fil', 'Informatique', 39.99),
('Enceinte Portable', 'Audio', 79.99),
('Montre Connectée', 'Wearable', 249.99),
('Webcam HD', 'Informatique', 69.99);

INSERT INTO clients (nom, prenom, email, ville, date_inscription, statut) VALUES
('Dupont', 'Marie', 'marie.dupont@email.com', 'Paris', '2023-01-15', 'actif'),
('Martin', 'Jean', 'jean.martin@email.com', 'Lyon', '2023-03-22', 'actif'),
('Bernard', 'Sophie', 'sophie.bernard@email.com', 'Marseille', '2023-06-10', 'actif'),
('Petit', 'Pierre', 'pierre.petit@email.com', 'Paris', '2023-09-05', 'inactif'),
('Durand', 'Claire', 'claire.durand@email.com', 'Toulouse', '2024-01-18', 'actif'),
('Leroy', 'Thomas', 'thomas.leroy@email.com', 'Lyon', '2024-02-28', 'actif'),
('Moreau', 'Julie', 'julie.moreau@email.com', 'Bordeaux', '2024-04-12', 'actif'),
('Simon', 'Lucas', 'lucas.simon@email.com', 'Paris', '2024-06-30', 'inactif'),
('Laurent', 'Emma', 'emma.laurent@email.com', 'Lille', '2024-08-15', 'actif'),
('Michel', 'Hugo', 'hugo.michel@email.com', 'Nantes', '2024-10-01', 'actif'),
('Garcia', 'Léa', 'lea.garcia@email.com', 'Marseille', '2024-11-20', 'actif'),
('Roux', 'Antoine', 'antoine.roux@email.com', 'Paris', '2025-01-05', 'actif');

INSERT INTO commandes (client_id, produit_id, quantite, montant_total, date_commande, statut) VALUES
(1, 1, 1, 1299.99, '2023-02-10', 'completee'),
(1, 3, 2, 299.98, '2023-05-15', 'completee'),
(2, 2, 1, 899.99, '2023-04-20', 'completee'),
(3, 5, 1, 349.99, '2023-07-08', 'completee'),
(2, 4, 1, 89.99, '2023-09-12', 'completee'),
(4, 1, 1, 1299.99, '2023-10-01', 'annulee'),
(5, 6, 1, 599.99, '2024-02-14', 'completee'),
(6, 2, 1, 899.99, '2024-03-20', 'completee'),
(1, 7, 3, 119.97, '2024-04-05', 'completee'),
(7, 9, 1, 249.99, '2024-05-18', 'completee'),
(3, 8, 2, 159.98, '2024-06-22', 'completee'),
(8, 10, 1, 69.99, '2024-07-30', 'completee'),
(9, 1, 1, 1299.99, '2024-09-10', 'completee'),
(10, 3, 1, 149.99, '2024-11-05', 'completee'),
(5, 4, 2, 179.98, '2024-12-20', 'completee'),
(11, 2, 1, 899.99, '2025-01-10', 'completee'),
(12, 5, 1, 349.99, '2025-01-15', 'completee'),
(6, 9, 1, 249.99, '2025-01-25', 'en_cours'),
(2, 6, 1, 599.99, '2025-02-01', 'en_cours'),
(1, 10, 2, 139.98, '2025-02-05', 'en_cours');

-- ============================================
-- TABLE UTILISATEURS (Authentification JWT)
-- ============================================

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(200) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    allowed_tables JSONB NOT NULL DEFAULT '["clients", "produits", "commandes"]',
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- TABLE HISTORIQUE DES CONVERSATIONS
-- ============================================

CREATE TABLE conversation_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    user_id INTEGER REFERENCES users(id),
    question TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_history_session ON conversation_history(session_id);
CREATE INDEX idx_history_date ON conversation_history(created_at DESC);

-- ============================================
-- TABLE PGVECTOR (pour le RAG Schema)
-- Stocke les descriptions de la base, pas les données
-- ============================================

CREATE TABLE rag_schema (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(384)
);

-- Index pour la recherche vectorielle rapide (HNSW, plus performant pour petits datasets)
CREATE INDEX ON rag_schema USING hnsw (embedding vector_cosine_ops);
