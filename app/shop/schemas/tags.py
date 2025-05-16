from pydantic import BaseModel, Field


class TagBase(BaseModel):
    name: str = Field(max_length=50)


class TagView(TagBase):
    id: int

    class Config:
        # для создания объекта схемы из объекта модели БД
        from_attributes = True


class TagCreate(TagBase):
    pass


class TagUpdate(TagBase):
    name: str | None = None


class ProductTagJoinView(BaseModel):
    product_id: int
    tag_id: int

    class Config:
        # для создания объекта схемы из объекта модели БД
        from_attributes = True