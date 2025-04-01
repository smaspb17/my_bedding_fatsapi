# app/admin/admin_config.py

from sqladmin import Admin, ModelView

from app.db.models.shop import Category, Tag, Product, ProductImage

# from app.db.database import engine
from app.db.models.users import User

# from main import app


# Определяем класс для отображения User в админке
class UserAdmin(ModelView, model=User):
    name = "Пользователь"
    name_plural = "Пользователи"
    column_list = [User.id, User.email, User.phone_number, User.first_name, User.last_name, User.address, User.is_active]
    form_excluded_columns = [User.created, User.updated]
    can_create = True
    can_edit = True
    can_delete = False
    can_view_details = True


class CategoryAdmin(ModelView, model=Category):
    name = "Категория"
    name_plural = "Категории"
    column_list = [
        Category.id,
        Category.title,
        Category.description,
    ]  # Колонки для отображения
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class ProductAdmin(ModelView, model=Product):
    name = "Товар"
    name_plural = "Товары"
    column_list = [
        Product.id,
        Product.title,
        Product.is_available,
        Product.category_id,
        Product.created,
        Product.updated,
    ]
    form_excluded_columns = [Product.created, Product.updated]
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class TagAdmin(ModelView, model=Tag):
    name = "Тег"
    name_plural = "Теги"
    column_list = [Tag.id, Tag.name]  # Колонки для отображения
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class ProductImageAdmin(ModelView, model=ProductImage):
    name = "Изображение товара"
    name_plural = "Изображения товаров"
    column_list = [ProductImage.id, ProductImage.product_id, ProductImage.image_path]  # Колонки для отображения
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


def init_admin(app, engine):
    admin = Admin(app, engine)
    admin.add_view(UserAdmin)
    admin.add_view(CategoryAdmin)
    admin.add_view(ProductAdmin)
    admin.add_view(TagAdmin)
    admin.add_view(ProductImageAdmin)
