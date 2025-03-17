from pydantic import BaseModel


class ImageView(BaseModel):
    id: int
    image_path: str

    class Config:
        from_attributes = True
