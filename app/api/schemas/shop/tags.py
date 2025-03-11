from app.db.shop.models import TagBase


class TagView(TagBase):
    id: int


class TagCreate(TagBase):
    pass


class TagUpdate(TagBase):
    pass