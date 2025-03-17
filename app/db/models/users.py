import enum
from datetime import datetime, UTC, timezone
from typing import Annotated
from sqlalchemy import Column, Integer, String, ForeignKey, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, str_256, int_pk, created_at, updated_at


class User(Base):
    __tablename__ = "user"

    # id: Mapped[int] = mapped_column(primary_key=True)
    id: Mapped[int_pk]
    name: Mapped[str] = mapped_column(index=True)


# class Worker(Base):
#     __tablename__ = "worker"
#     id: Mapped[int] = mapped_column(Integer, primary_key=True)
#     username: Mapped[str]
#     resumes: Mapped[list["Resume"]] = relationship()
#
#
# class Workload(enum.Enum):
#     parttime = "parttime"
#     fulltime = "fulltime"
#
#
# class Resume(Base):
#     __tablename__ = "resume"
#     id: Mapped[int] = mapped_column(Integer, primary_key=True)
#     title: Mapped[str_256]
#     compensation: Mapped[int | None]
#     workload: Mapped[Workload]
#     worker_id: Mapped[int] = mapped_column(
#         ForeignKey("worker.id", ondelete="CASCADE")
#     )  # рекомендуется
#     created_at: Mapped[created_at]
#     updated_at: Mapped[updated_at]
#     worker: Mapped["Worker"] = relationship()



# class Test(Base):
#     id: Mapped[intpk]
#     name: Mapped[str | None] = mapped_column(String(50), nullable=True)