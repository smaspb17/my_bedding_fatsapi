from datetime import datetime, UTC
from typing import Annotated

from sqlalchemy import String, text, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, mapped_column

str_255 = Annotated[str, 255]


class Base(DeclarativeBase):
    type_annotation_map = {str_255: String(255)}

    def __repr__(self):
        cols = []
        for col in self.__table__.columns.keys():
            cols.append(f"{col}={getattr(self, col)}")

        return f"<{self.__class__.__name__} {', '.join(cols)}>"


# Общие аннотации
int_pk = Annotated[int, mapped_column(primary_key=True)]
created_at = Annotated[
    datetime,
    mapped_column(
        TIMESTAMP(timezone=True),
        default_factory=lambda: datetime.now(UTC),
        server_default=text("now()"),
    ),
]
updated_at = Annotated[
    datetime,
    mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        default_factory=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    ),
]
