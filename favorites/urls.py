from django.urls import path

from . import views

app_name = "favorites"

urlpatterns = [
    path("", views.favorite_list_detail, name="favorite-list"),
    path("add/", views.favorite_add, name="favorite-add"),
    path("remove/", views.favorite_remove, name="favorite-remove"),
    path("clear/", views.favorite_clear, name="favorite-clear"),
]
