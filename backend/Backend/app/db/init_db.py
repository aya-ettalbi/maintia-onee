from sqlalchemy import select

from app.core.config import settings
from app.core.enums import Role, UserStatus
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import User  # noqa: F401 - ensures all models are imported


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == settings.FIRST_ADMIN_EMAIL.lower()))
        if admin is None:
            admin = User(
                first_name=settings.FIRST_ADMIN_FIRST_NAME,
                last_name=settings.FIRST_ADMIN_LAST_NAME,
                email=settings.FIRST_ADMIN_EMAIL.lower(),
                hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
                role=Role.ADMIN.value,
                status=UserStatus.ACTIVE.value,
            )
            db.add(admin)
            db.commit()
