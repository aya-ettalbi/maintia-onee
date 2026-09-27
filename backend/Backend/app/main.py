import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.init_db import init_db
from app.services.rag_chat import get_retriever


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()

    # Charge une seule fois le modèle d'embedding et le Cross-Encoder.
    # L'application n'annonce 'startup complete' qu'après le préchargement.
    await asyncio.to_thread(get_retriever)

    yield


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        description=(
            "API de gestion du parc informatique, des demandes, des interventions, "
            "du stock, du reporting, des recommandations et des modules IA."
        ),
        version="0.2.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @application.get("/", tags=["Accueil"])
    def root() -> dict[str, str]:
        return {
            "application": settings.APP_NAME,
            "version": "0.2.0",
            "status": "active",
            "docs": "/docs",
        }

    return application


app = create_application()
