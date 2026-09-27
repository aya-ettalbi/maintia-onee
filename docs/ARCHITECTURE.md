# Architecture MaintIA ONEE

## Vue générale

![Architecture générale](diagrams/architecture-generale.png)

## Composants

### Frontend
- Next.js
- React
- TypeScript
- Tailwind CSS

### Backend
- FastAPI
- SQLAlchemy
- Pydantic
- Alembic

### Données
- PostgreSQL pour les données métier et historiques
- Qdrant pour la recherche vectorielle

### IA
- Sentence Transformers pour les embeddings
- CrossEncoder pour le reranking
- RAG pour la contextualisation
- OpenRouter pour la génération contrôlée

## Workflow

![Workflow fonctionnel](diagrams/workflow-fonctionnel.png)

## Technologies

![Technologies](diagrams/technologies.png)
