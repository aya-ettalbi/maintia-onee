import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_maintenance.db"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-longer-than-32-bytes"
os.environ["FIRST_ADMIN_EMAIL"] = "admin@test.local"
os.environ["FIRST_ADMIN_PASSWORD"] = "AdminTest123!"

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def clean_database():
    """
    Prépare une base SQLite propre avant les tests
    et libère correctement les connexions à la fin.
    """

    database_file = Path("test_maintenance.db")

    # Fermer les anciennes connexions éventuelles.
    engine.dispose()

    # Supprimer une ancienne base de test.
    database_file.unlink(missing_ok=True)

    # Créer les tables nécessaires.
    Base.metadata.create_all(bind=engine)

    try:
        yield

    finally:
        # Supprimer les tables après les tests.
        Base.metadata.drop_all(bind=engine)

        # Fermer les connexions conservées dans le pool SQLAlchemy.
        engine.dispose()

        # Supprimer le fichier de test.
        database_file.unlink(missing_ok=True)


@pytest.fixture()
def client():
    """
    Fournit un client HTTP de test pour FastAPI.
    """

    with TestClient(app) as test_client:
        yield test_client