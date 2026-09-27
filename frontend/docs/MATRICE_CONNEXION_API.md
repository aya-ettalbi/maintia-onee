# Matrice Frontend ↔ FastAPI

| Module | Principales routes intégrées |
|---|---|
| Authentification | `POST /auth/login`, `GET /auth/me` |
| Utilisateurs | `GET/POST/PATCH /users`, activation, désactivation, reset password |
| Organisation | `GET/POST/PATCH /services`, `/locations`, `/equipment-categories` |
| Équipements | CRUD, archive, activate, assignments, history, KPI |
| Demandes | CRUD, changement de statut, annulation |
| Interventions | CRUD, statuts, historique, actions, pièces, close, cancel |
| Stock | pièces, mouvements, summary, alerts, shortage-risks |
| Historique ONEE | summary, requests, tasks, supplies, incidents, analytics |
| Maintenance préventive | plans, due, execute, executions |
| KPI et rapports | maintenance, equipment KPI, monthly, generate, archive |
| IA | chat RAG, triage, diagnostic, risk score/assessment, recurrent failures |
| Prévisions | create, latest, history, high-risk, summary, validate, batch, runs |
| Recommandations | list, generate, update |
| Notifications | list, read, read-all, unread-count |
| Audit | `GET /audit-logs` |

Le contrat exact est conservé dans `docs/openapi_backend_ai_stable.json`.
