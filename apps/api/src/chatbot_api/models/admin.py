from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdPk, Timestamped
from .enums import AdminRole


class Admin(IdPk, Timestamped, Base):
    __tablename__ = "admins"

    cognito_sub: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[AdminRole] = mapped_column(
        Enum(AdminRole, name="admin_role"),
        nullable=False,
        default=AdminRole.admin,
    )
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
