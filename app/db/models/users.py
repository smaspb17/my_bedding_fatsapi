import enum
from datetime import datetime, UTC, timezone
from typing import Annotated
from sqlalchemy import Column, Integer, String, ForeignKey, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, str_256, int_pk, created_at, updated_at


class User(Base):
    __tablename__ = "user"

    id: Mapped[int_pk]
    name: Mapped[str] = mapped_column(index=True)
