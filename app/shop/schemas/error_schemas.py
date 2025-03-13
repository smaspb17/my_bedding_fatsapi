from pydantic import BaseModel


class NotFoundErrorSchema(BaseModel):
    detail: str


class BadRequestErrorSchema(BaseModel):
    detail: str
    # type_error: str
    # message: str
    # location: str
