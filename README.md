# MaintIA ONEE

> **Intelligent IT Maintenance Management Platform**  
> A full-stack web platform for IT asset management, maintenance operations, analytics, AI-assisted diagnostics, RAG-based support, and failure-risk prediction.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Main Objectives](#main-objectives)
3. [Technology Stack](#technology-stack)
4. [System Architecture](#system-architecture)
5. [Professional Workflow](#professional-workflow)
6. [Platform Demo](#platform-demo)
7. [Core Features](#core-features)
8. [Project Structure](#project-structure)
9. [Installation](#installation)
10. [Environment Variables](#environment-variables)
11. [Security](#security)
12. [Author](#author)

---

## Project Overview

**MaintIA ONEE** is an intelligent maintenance management platform designed to centralize and optimize the management of an IT infrastructure.

The platform combines operational maintenance workflows with analytics and artificial intelligence to provide a unified environment for:

- IT asset management;
- maintenance requests;
- corrective and preventive interventions;
- equipment assignments;
- stock monitoring;
- historical analytics;
- AI-assisted diagnostics;
- RAG-based support;
- failure-risk prediction;
- intelligent recommendations.

The solution is built with a modern full-stack architecture using **Next.js**, **FastAPI**, **PostgreSQL**, **Qdrant**, and AI services.

---

## Main Objectives

MaintIA ONEE was designed to:

- centralize IT asset information in a single platform;
- improve maintenance request tracking;
- structure intervention management;
- support preventive maintenance planning;
- exploit historical maintenance data;
- provide operational dashboards and KPIs;
- assist technicians with AI-powered diagnostics;
- retrieve similar historical cases using semantic search;
- estimate equipment failure risk;
- generate maintenance recommendations while keeping human validation in the loop.

---

## Technology Stack

### Frontend

- **Next.js**
- **React**
- **TypeScript**
- **Tailwind CSS**
- **Recharts**
- **Lucide React**

### Backend

- **Python**
- **FastAPI**
- **SQLAlchemy**
- **Pydantic**
- **Alembic**

### Data Layer

- **PostgreSQL**
- **Qdrant Vector Database**

### AI & RAG

- **Sentence Transformers**
- **CrossEncoder**
- **Retrieval-Augmented Generation (RAG)**
- **OpenRouter**

### Infrastructure & Development

- **Docker**
- **Git**
- **GitHub**
- **PowerShell**
- **Windows**

---

## System Architecture

The platform follows a modular architecture where the frontend communicates with a REST API, while the backend handles business logic, persistent data, vector search, and AI services.

![MaintIA ONEE Architecture](docs/diagrams/architecture-generale.png)

### Main Data Flow

```text
User
  |
  v
Next.js Frontend
  |
  v
FastAPI Backend
  |--------------------|
  |                    |
  v                    v
PostgreSQL          Qdrant
  |                    |
  |                    v
  |               Vector Search
  |                    |
  |                    v
  |                RAG Layer
  |                    |
  |                    v
  |                OpenRouter
  |                    |
  |--------------------|
           |
           v
      API Response
           |
           v
      Web Interface
```

---

## Professional Workflow

The application workflow connects operational maintenance activities with analytics and AI-assisted decision support.

![MaintIA ONEE Workflow](docs/diagrams/workflow-fonctionnel.png)

### Workflow

```text
Authentication
      |
      v
Control Center
      |
      +-----------------------------+
      |              |              |
      v              v              v
IT Assets        Requests       Interventions
      |              |              |
      +--------------+--------------+
                     |
                     v
          Maintenance Management
                     |
          +----------+----------+
          |                     |
          v                     v
      Analytics            Preventive
                                |
                                v
                         AI Assistant
                                |
                  +-------------+-------------+
                  |                           |
                  v                           v
          Similar Case Search         Failure Prediction
                  |                           |
                  +-------------+-------------+
                                |
                                v
                     Recommendations
                                |
                                v
                       Human Validation
```

---

## Technologies Overview

![Technologies Used](docs/diagrams/technologies.png)

---

# Platform Demo

## 1. Login Interface

The login page provides secure access to the platform while introducing the ONEE visual identity.

![Login Interface](docs/screenshots/01-login.png)

### Highlights

- secure authentication;
- professional institutional design;
- direct access to the maintenance platform.

---

## 2. Main Control Center

The main dashboard provides a consolidated operational overview.

![Main Dashboard](docs/screenshots/02-dashboard.png)

### Dashboard Information

- IT asset status;
- open maintenance requests;
- active interventions;
- high-risk equipment;
- availability indicators;
- stock alerts;
- maintenance activity overview.

---

## 3. Requests and Interventions

This section displays recent maintenance activity in a clear operational view.

![Requests and Interventions](docs/screenshots/03-demandes-interventions.png)

### Information Displayed

- latest requests;
- priority levels;
- request status;
- recent interventions;
- preventive maintenance deadlines;
- detected risks;
- recommendations.

---

## 4. Historical Analytics

The analytics module transforms historical maintenance data into operational insights.

![Historical Analytics](docs/screenshots/04-analytique-historique.png)

### Analytics Capabilities

- number of analyzed requests;
- number of analyzed tasks;
- available historical solutions;
- average processing time;
- monthly request evolution;
- status distribution;
- maintenance trend analysis.

---

## 5. IT Asset Management

The IT asset module provides a centralized inventory of equipment.

![IT Asset Management](docs/screenshots/05-parc-informatique.png)

### Managed Information

- equipment identifier;
- category;
- operational status;
- assigned department;
- location;
- commissioning date;
- equipment history.

---

## 6. Equipment Assignment

This module manages equipment assignment to users or departments.

![Equipment Assignment](docs/screenshots/06-affectations-equipement.png)

### Capabilities

- view current assignments;
- create new assignments;
- track assignment history;
- associate equipment with users or services.

---

## 7. MaintIA Assistant — Diagnostic Mode

The diagnostic assistant searches historical maintenance cases using semantic similarity.

![AI Diagnostic Assistant](docs/screenshots/07-assistant-diagnostic.png)

### Diagnostic Process

```text
User Symptom
     |
     v
Embedding Generation
     |
     v
Qdrant Vector Search
     |
     v
Similarity Ranking
     |
     v
Historical Diagnosis
     |
     v
Suggested Historical Solution
```

### Output

- similar historical cases;
- similarity score;
- known diagnosis;
- associated solution;
- contextual maintenance information.

---

## 8. Failure Prediction

The prediction module estimates the risk associated with an equipment failure.

![Failure Prediction](docs/screenshots/08-prevision-panne.png)

### Prediction Output

- risk score;
- confidence level;
- contributing factors;
- business explanation;
- recommended actions;
- human validation before operational action.

---

## 9. MaintIA Assistant — RAG Chat

The conversational assistant helps users query maintenance information through a RAG pipeline.

![RAG Chat](docs/screenshots/09-chat-rag.png)

### Example Uses

- describe a technical symptom;
- search maintenance history;
- ask for similar incidents;
- retrieve known solutions;
- obtain contextualized assistance.

### RAG Workflow

```text
User Question
     |
     v
Text Embedding
     |
     v
Qdrant Retrieval
     |
     v
Relevant Historical Context
     |
     v
CrossEncoder Reranking
     |
     v
Prompt Construction
     |
     v
OpenRouter LLM
     |
     v
Contextualized Answer
```

---

# Core Features

## Operational Management

- IT asset inventory;
- equipment assignments;
- maintenance requests;
- corrective interventions;
- preventive interventions;
- spare-parts and stock monitoring;
- operational status tracking.

## Analytics

- historical maintenance analysis;
- KPI visualization;
- request evolution;
- intervention monitoring;
- status distribution;
- maintenance trends.

## Artificial Intelligence

- RAG conversational assistant;
- semantic search;
- similar-case retrieval;
- AI-assisted diagnosis;
- failure-risk estimation;
- maintenance recommendations.

## Decision Support

The platform is designed as a decision-support tool.  
AI-generated outputs are intended to assist users and can be validated by a human before operational decisions are applied.

---

# Project Structure

```text
Projet_Maintenance_Intelligente_ONEE/
│
├── README.md
├── .gitignore
│
├── docs/
│   ├── assets/
│   │   ├── onee-original.png
│   │   └── onee-banner-adaptee.png
│   │
│   ├── diagrams/
│   │   ├── architecture-generale.png
│   │   ├── workflow-fonctionnel.png
│   │   └── technologies.png
│   │
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
│   │
│   ├── ARCHITECTURE.md
│   └── INSTALLATION.md
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── docs/
│   ├── hooks/
│   ├── lib/
│   ├── public/
│   ├── scripts/
│   ├── styles/
│   ├── .env.local.example
│   ├── package.json
│   ├── package-lock.json
│   └── tsconfig.json
│
└── backend/
    └── Backend/
        ├── app/
        ├── alembic/
        ├── scripts/
        ├── tests/
        ├── .env.example
        ├── alembic.ini
        ├── pytest.ini
        ├── requirements.txt
        └── requirements.lock.txt
```

### `frontend/`

Contains the user interface and client-side logic:

- Next.js pages;
- reusable React components;
- frontend API integration;
- charts and visualizations;
- authentication interface;
- user interactions.

### `backend/Backend/`

Contains the application backend:

- FastAPI routes;
- business services;
- database models;
- validation schemas;
- Alembic migrations;
- authentication logic;
- analytics;
- AI and RAG services.

### `docs/`

Contains the public project documentation:

- screenshots;
- architecture diagrams;
- technical documentation;
- installation documentation.

---

# Installation

## Requirements

Make sure the following tools are installed:

- Python 3.12+
- Node.js
- npm
- Docker Desktop
- Git

---

## Backend Setup

Navigate to the backend:

```powershell
cd backend\Backend
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create the local environment file:

```powershell
Copy-Item .env.example .env
```

Start the required containers:

```powershell
docker start maintenance_onee_db
docker start maintenance_onee_qdrant
```

Run FastAPI:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

---

## Frontend Setup

Navigate to the frontend:

```powershell
cd frontend
```

Install dependencies:

```powershell
npm install
```

Create the frontend environment file:

```powershell
Copy-Item .env.local.example .env.local
```

Run the application:

```powershell
npm run dev
```

Application URL:

```text
http://localhost:3000
```

---

# Environment Variables

## Backend Example

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

## Frontend Example

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
```

---

# Security

Never commit sensitive local files such as:

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

Recommended practices:

- keep real credentials only in local `.env` files;
- publish only `.env.example` files with placeholder values;
- never commit API keys or secrets;
- keep private operational data outside the public repository;
- rotate any credential that has been accidentally exposed.

---

# Author
---

---

## Connect with me


- GitHub: https://github.com/aya-ettalbi
- LinkedIn: https://www.linkedin.com/in/aya-ettalbi-0a5012336

### Author

**Aya Ettalbi**  
Engineering Student in **Big Data & Artificial Intelligence**  
ENSA Tétouan

Project: **MaintIA ONEE — Intelligent IT Maintenance Management Platform**
