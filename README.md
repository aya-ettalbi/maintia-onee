# MaintIA ONEE

> **Plateforme intelligente de maintenance du parc informatique**  
> Une solution web complète pour la gestion du parc, des demandes, des interventions, du stock, de la maintenance préventive et des fonctionnalités d’intelligence artificielle.

---

## Table des matières

1. [Présentation du projet](#présentation-du-projet)
2. [Objectifs](#objectifs)
3. [Stack technique](#stack-technique)
4. [Architecture et workflow](#architecture-et-workflow)
5. [Démonstration visuelle de la plateforme](#démonstration-visuelle-de-la-plateforme)
6. [Fonctionnalités principales](#fonctionnalités-principales)
7. [Structure du projet](#structure-du-projet)
8. [Installation et lancement](#installation-et-lancement)
9. [Variables d’environnement](#variables-denvironnement)
10. [Bonnes pratiques et sécurité](#bonnes-pratiques-et-sécurité)
11. [Auteur](#auteur)

---

## Présentation du projet

**MaintIA ONEE** est une plateforme de pilotage et d’aide à la décision dédiée à la maintenance du parc informatique.  
Le projet centralise dans une seule interface :

- la gestion du **parc informatique** ;
- le suivi des **demandes** ;
- la gestion des **interventions** ;
- le pilotage du **stock** ;
- la **maintenance préventive** ;
- l’**analyse historique** ;
- l’**assistant IA** basé sur le RAG ;
- les **prévisions de panne** ;
- les **recommandations intelligentes**.

L’objectif est de proposer une plateforme moderne, exploitable et évolutive, adaptée à un contexte métier réel.

---

## Objectifs

Ce projet a été conçu pour :

- améliorer la visibilité sur l’état du parc informatique ;
- structurer la gestion des demandes et interventions ;
- exploiter l’historique de maintenance dans un cadre analytique ;
- aider les utilisateurs grâce à des outils IA ;
- produire des prévisions et recommandations exploitables ;
- centraliser plusieurs briques dans une architecture cohérente.

---

## Stack technique

### Frontend
- **Next.js**
- **React**
- **TypeScript**
- **Tailwind CSS**
- **Recharts**
- **Lucide React**

### Backend
- **FastAPI**
- **Python**
- **SQLAlchemy**
- **Pydantic**
- **Alembic**

### Base de données & recherche
- **PostgreSQL**
- **Qdrant**

### IA / RAG
- **Sentence Transformers**
- **CrossEncoder**
- **OpenRouter**
- **Retrieval-Augmented Generation (RAG)**

### Infrastructure
- **Docker**
- **Git / GitHub**
- **PowerShell / Windows**

---

## Architecture et workflow

### Architecture générale

![Architecture générale](docs/diagrams/architecture-generale.png)

### Workflow fonctionnel

![Workflow fonctionnel](docs/diagrams/workflow-fonctionnel.png)

### Technologies utilisées

![Technologies utilisées](docs/diagrams/technologies.png)

### Explication du workflow

Le fonctionnement général de la plateforme suit ce cycle :

1. **L’utilisateur** accède à l’interface web via le frontend.
2. Le **frontend Next.js** communique avec le **backend FastAPI**.
3. Le backend traite la logique métier :
   - authentification,
   - gestion des équipements,
   - demandes,
   - interventions,
   - stock,
   - analytique,
   - modules IA.
4. Les données métiers sont stockées dans **PostgreSQL**.
5. Les données vectorielles et la recherche sémantique passent par **Qdrant**.
6. Les modules IA utilisent :
   - les **embeddings**,
   - le **reranking** via CrossEncoder,
   - **OpenRouter** pour la génération de réponse contrôlée.
7. Les résultats sont renvoyés au frontend pour affichage et interaction.

---

# Démonstration visuelle de la plateforme

## 1) Page de connexion

La page de connexion introduit l’identité visuelle du projet avec une interface propre et professionnelle.

![Connexion](docs/screenshots/01-login.png)

**Ce qu’on y retrouve :**
- accès sécurisé ;
- intégration de l’identité visuelle ONEE ;
- entrée vers toute la plateforme.

---

## 2) Centre de pilotage global

Cette vue centralise les indicateurs les plus importants du système.

![Centre de pilotage](docs/screenshots/02-dashboard.png)

**Contenu principal :**
- parc informatique ;
- demandes ouvertes ;
- interventions actives ;
- risques élevés ;
- indicateurs de disponibilité ;
- synthèse du stock critique.

---

## 3) Dernières demandes et interventions

Cette vue donne un aperçu rapide des activités récentes.

![Demandes et interventions](docs/screenshots/03-demandes-interventions.png)

**Éléments affichés :**
- dernières demandes ;
- priorité et statut ;
- interventions récentes ;
- échéances préventives ;
- risques prédictifs ;
- recommandations.

---

## 4) Analytique historique

Le module analytique exploite les historiques importés ou générés par la plateforme.

![Analytique historique](docs/screenshots/04-analytique-historique.png)

**Fonctions mises en avant :**
- volume de demandes analysées ;
- volume de tâches analysées ;
- solutions disponibles ;
- délai moyen historique ;
- évolution mensuelle des demandes ;
- répartition des statuts.

---

## 5) Parc informatique

Le module “Parc informatique” permet de gérer l’inventaire des équipements.

![Parc informatique](docs/screenshots/05-parc-informatique.png)

**Informations suivies :**
- liste des équipements ;
- catégorie ;
- statut ;
- service ;
- localisation ;
- mise en service ;
- actions de consultation et gestion.

---

## 6) Affectation des équipements

Cette vue détaille l’affectation d’un équipement à un utilisateur ou un service.

![Affectation équipement](docs/screenshots/06-affectations-equipement.png)

**Ce module permet :**
- de consulter les affectations ;
- d’ajouter une nouvelle affectation ;
- de garder une trace des affectations existantes ;
- de lier un équipement à un utilisateur/service.

---

## 7) Assistant MaintIA — mode diagnostic

Le module d’assistance IA permet de rechercher des cas similaires à partir d’un symptôme.

![Assistant diagnostic](docs/screenshots/07-assistant-diagnostic.png)

**Fonctionnement :**
- saisie d’un symptôme ;
- recherche de cas similaires ;
- affichage d’un score de similarité ;
- diagnostic associé ;
- solution historique trouvée.

---

## 8) Prévisions de panne

Le module de prévision fournit un risque estimé pour un équipement.

![Prévision de panne](docs/screenshots/08-prevision-panne.png)

**Ce qu’il inclut :**
- score de risque ;
- niveau de confiance ;
- facteurs calculés ;
- explication métier ;
- actions recommandées ;
- validation humaine avant décision.

---

## 9) Assistant MaintIA — Chat RAG

Le copilote conversationnel aide à interroger l’historique et à assister le support.

![Chat RAG](docs/screenshots/09-chat-rag.png)

**Utilisation :**
- poser une question libre ;
- demander un historique ;
- décrire un symptôme ;
- recevoir une réponse contextualisée.

---

# Fonctionnalités principales

## Gestion métier
- gestion des équipements ;
- gestion du parc ;
- demandes et suivi de statut ;
- interventions correctives et préventives ;
- gestion du stock ;
- affectations ;
- KPI et reporting.

## Intelligence artificielle
- assistant conversationnel ;
- recherche de cas similaires ;
- diagnostic basé sur l’historique ;
- estimation du risque de panne ;
- recommandations automatiques.

## Pilotage
- vue générale consolidée ;
- analytique historique ;
- indicateurs de performance ;
- synthèse opérationnelle.

---

# Structure du projet

```text
Projet_Maintenance_Intelligente_ONEE/
│
├── README.md
├── docs/
│   ├── assets/
│   │   ├── onee-original.png
│   │   └── onee-banner-adaptee.png
│   ├── diagrams/
│   │   ├── architecture-generale.png
│   │   ├── workflow-fonctionnel.png
│   │   └── technologies.png
│   ├── screenshots/
│   │   ├── 01-login.png
│   │   ├── 02-dashboard.png
│   │   ├── 03-demandes-interventions.png
│   │   ├── 04-analytique-historique.png
│   │   ├── 05-parc-informatique.png
│   │   ├── 06-affectations-equipement.png
│   │   ├── 07-assistant-diagnostic.png
│   │   ├── 08-prevision-panne.png
│   │   └── 09-chat-rag.png
│   ├── ARCHITECTURE.md
│   └── INSTALLATION.md
│
├── frontend_maintenance_onee_definitif_windows/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   ├── public/
│   ├── scripts/
│   ├── styles/
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   └── .env.local.example
│
└── 07_Developpement/
    └── Backend/
        ├── app/
        ├── alembic/
        ├── scripts/
        ├── tests/
        ├── requirements.txt
        ├── requirements.lock.txt
        ├── alembic.ini
        ├── pytest.ini
        └── .env.example
```

### Explication des dossiers

### `frontend_maintenance_onee_definitif_windows/`
Contient toute l’interface utilisateur :
- pages Next.js ;
- composants UI ;
- hooks React ;
- logique de présentation ;
- intégration avec l’API.

### `07_Developpement/Backend/`
Contient le backend applicatif :
- routes API ;
- services métier ;
- modèles ;
- schémas ;
- migrations ;
- logique IA et RAG.

### `docs/`
Contient la documentation de présentation :
- images de démonstration ;
- diagrammes ;
- documentation architecture et installation.

---

# Installation et lancement

## 1. Prérequis
- Python 3.12+
- Node.js
- npm
- Docker Desktop
- Git

---

## 2. Lancer le backend

```powershell
cd 07_Developpement\Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
docker start maintenance_onee_db
docker start maintenance_onee_qdrant
$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Documentation API :

```text
http://127.0.0.1:8000/docs
```

---

## 3. Lancer le frontend

```powershell
cd frontend_maintenance_onee_definitif_windows
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Application :

```text
http://localhost:3000
```

---

# Variables d’environnement

## Backend
Exemple de configuration :

```env
APP_NAME=Plateforme Intelligente de Maintenance ONEE
ENVIRONMENT=development
DEBUG=true
API_V1_PREFIX=/api/v1

DATABASE_URL=postgresql+psycopg://maintenance_app:CHANGE_ME@127.0.0.1:5432/maintenance_onee

SECRET_KEY=CHANGE_ME_WITH_A_LONG_RANDOM_SECRET
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

FIRST_ADMIN_EMAIL=admin@onee.ma
FIRST_ADMIN_PASSWORD=CHANGE_ME

CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

QDRANT_URL=http://127.0.0.1:6333
QDRANT_COLLECTION=maintenance_onee_rag

RAG_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
RAG_BATCH_SIZE=64
RAG_MIN_SCORE=0.30
RAG_TOP_K=4
RAG_MAX_CONTEXT_CHARS=8000

OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=CHANGE_ME
OPENROUTER_MODEL=CHANGE_ME
```

## Frontend
Exemple :

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
```

---

# Bonnes pratiques et sécurité

À ne jamais pousser sur GitHub :

```text
.env
.env.local
.venv/
node_modules/
.next/
*.db
*.dump
data/
```

Bonnes pratiques recommandées :

- utiliser `.env.example` et `.env.local.example` pour les exemples ;
- ne jamais publier les vraies clés API ;
- garder les données sensibles localement ;
- documenter clairement le projet à la racine.

---

# Auteur

**Aya Ettalbi**  
Élève ingénieure en Big Data & Intelligence Artificielle  
**ENSA Tétouan**

Projet : **MaintIA ONEE — Plateforme Intelligente de Maintenance**
