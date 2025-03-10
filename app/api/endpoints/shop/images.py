


# class ProductImage(models.Model):
#     product = models.ForeignKey(
#         Product,
#         on_delete=models.CASCADE,
#         related_name='product_images',
#         verbose_name='Товар'
#     )
#     image = models.ImageField(
#         upload_to='products/%Y/%m/%d/',
#         verbose_name='Фото'
#     )