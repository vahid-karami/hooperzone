from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("product/<slug:product_slug>/", views.product_reviews, name="product-reviews"),
    path("product/<slug:product_slug>/create/", views.review_create, name="review-create"),
    path("<int:review_id>/update/", views.review_update, name="review-update"),
    path("<int:review_id>/delete/", views.review_delete, name="review-delete"),
]
