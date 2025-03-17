from pydantic import BaseModel, Field


class CategoryBase(BaseModel):
    title: str = Field(max_length=100, unique=True)
    description: str | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryView(CategoryBase):
    id: int


class CategoryDelete(BaseModel):
    id: int = Field(json_schema_extra={'example': '1'})
    message: str = Field(json_schema_extra={'example': 'Object deleted successfully'})


class CategoryUpdate(CategoryBase):
    title: str | None = None
    description: str | None = None
