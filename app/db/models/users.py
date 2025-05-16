from sqlalchemy import Enum
from datetime import datetime

from passlib.handlers.bcrypt import bcrypt
from pydantic import field_validator
from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, DatetimeTZ, created_at, updated_at, int_pk
from ...auth.schemas import RoleEnum


class User(Base):
    __tablename__ = "user"

    id: Mapped[int_pk]
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=False, index=True)
    is_email_confirmed: Mapped[bool | None] = mapped_column(default=False)
    email_confirm_token: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    email_confirm_time: Mapped[created_at | None] = mapped_column(
        nullable=True
    )
    password_reset_token: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    password_reset_time: Mapped[DatetimeTZ | None] = mapped_column(
        nullable=True
    )
    phone_number: Mapped[str] = mapped_column(String(12), index=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    photo: Mapped[str | None] = mapped_column(nullable=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created: Mapped[created_at]
    updated: Mapped[updated_at]
    hashed_password: Mapped[str | None] = mapped_column(nullable=True)
    # role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum, create_type=True), nullable=False, default=RoleEnum.BUYER)
    role: Mapped[RoleEnum] = mapped_column(
        Enum(RoleEnum, create_type=True),
        nullable=False,
        default=RoleEnum.BUYER,
    )

    @field_validator("hashed_password")
    def validate_hashed_password(cls, value):
        # Проверка, что хэш соответствует ожидаемому формату bcrypt
        if not bcrypt.identify(value):
            raise ValueError("Invalid hashed password format")
        return value


# class Role(Base):
#     __tablename__ = 'role'
#     id: Mapped[int_pk]
#     name: Mapped[str] = mapped_column(String(10), unique=True)
#
#     # объектная связь
#     users: Mapped[list['User']] = relationship(
#         'User', back_populates='role'
#     )


# class Permission(Base):
#     __tablename__ = 'permission'
#     id: Mapped[int_pk]
#     name: Mapped[str] = mapped_column(String(10), unique=True)
#
#
# class Group(Base):
#     __tablename__ = 'group'
#     id: Mapped[int_pk]
#     name: Mapped[str] = mapped_column(String(10), unique=True)
#
#     # объектная связь
#     permissions: Mapped[list['Permission']] = relationship(
#         'Permission', secondary='group_permission')
#
#
# class GroupPermission(Base):
#     __tablename__ = 'group_permission'
#     group_id: Mapped[int] = mapped_column(
#         ForeignKey('group.id'), primary_key=True)
#     permission_id: Mapped[int] = mapped_column(
#         ForeignKey('permission.id'), primary_key=True)
