from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import Role, UserStatus
from app.db.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(40), default=Role.REQUESTER.value, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=UserStatus.ACTIVE.value, nullable=False)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id"), nullable=True)
