from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from products.models import Product

from .models import FavoriteItem, FavoriteList
from .serializers import FavoriteListSerializer


def get_or_create_favorite_list(user):
    favorite_list, _ = FavoriteList.objects.get_or_create(user=user)
    return favorite_list


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def favorite_list_detail(request):
    favorite_list = get_or_create_favorite_list(request.user)
    return Response(FavoriteListSerializer(favorite_list).data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def favorite_add(request):
    favorite_list = get_or_create_favorite_list(request.user)

    product_id = request.data.get("product_id")
    if not product_id:
        return Response(
            {"error": "product_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        product = Product.objects.get(id=product_id, is_active=True)
    except (Product.DoesNotExist, ValueError, TypeError):
        return Response(
            {"error": "Product not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    item, created = FavoriteItem.objects.get_or_create(
        favorite_list=favorite_list,
        product=product,
    )

    if not created:
        # Same shape as every other favorites response: the client stores it
        # as the whole favorites list.
        return Response(FavoriteListSerializer(favorite_list).data, status=status.HTTP_200_OK)

    return Response(FavoriteListSerializer(favorite_list).data, status=status.HTTP_201_CREATED)


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def favorite_remove(request):
    favorite_list = get_or_create_favorite_list(request.user)

    product_id = request.data.get("product_id")
    if not product_id:
        return Response(
            {"error": "product_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        deleted, _ = FavoriteItem.objects.filter(
            favorite_list=favorite_list,
            product_id=product_id,
        ).delete()
    except (ValueError, TypeError):
        deleted = 0

    if not deleted:
        return Response(
            {"error": "Product not found in favorites."},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(FavoriteListSerializer(favorite_list).data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def favorite_clear(request):
    favorite_list = get_or_create_favorite_list(request.user)
    favorite_list.items.all().delete()
    return Response(FavoriteListSerializer(favorite_list).data, status=status.HTTP_200_OK)
