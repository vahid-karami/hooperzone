from django.conf import settings
from django.db import models


class FavoriteList(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_list",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "favorite_lists"

    def __str__(self):
        return f"Favorites for {self.user.phone}"


class FavoriteItem(models.Model):
    favorite_list = models.ForeignKey(FavoriteList, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "favorite_items"
        unique_together = ["favorite_list", "product"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} in {self.favorite_list}"
