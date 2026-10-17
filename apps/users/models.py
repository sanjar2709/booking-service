from enum import StrEnum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from apps.common.models import TimeStampedMixin
from core.db import Base


class Role(StrEnum):
    ADMIN = 'admin'
    CLIENT = 'client'


class User(TimeStampedMixin, Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(150), default='')
    phone: Mapped[str] = mapped_column(String(20), default='')
    role: Mapped[Role] = mapped_column(
        Enum(Role, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e]),
        default=Role.CLIENT,
    )
    is_active: Mapped[bool] = mapped_column(default=True)

    def __repr__(self):
        return f'<User {self.email}>'

    @property
    def is_admin(self):
        return self.role == Role.ADMIN
