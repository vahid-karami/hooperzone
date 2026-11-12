from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from orders.models import Order, OrderItem
from products.models import Product

from .models import Review
from .serializers import ReviewCreateSerializer, ReviewSerializer


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def product_reviews(request, product_slug):
    try:
        product = Product.objects.get(slug=product_slug, is_active=True)
    except Product.DoesNotExist:
        return Response(
            {"error": "Product not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    reviews = Review.objects.filter(product=product)
    return Response(ReviewSerializer(reviews, many=True).data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def review_create(request, product_slug):
    try:
        product = Product.objects.get(slug=product_slug, is_active=True)
    except Product.DoesNotExist:
        return Response(
            {"error": "Product not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if Review.objects.filter(user=request.user, product=product).exists():
        return Response(
            {"error": "You have already reviewed this product."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = ReviewCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    has_ordered = (
        OrderItem.objects.filter(
            order__user=request.user,
            order__status=Order.STATUS_DELIVERED,
            product=product,
        )
        .exists()
    )

    review = Review.objects.create(
        user=request.user,
        product=product,
        is_verified_purchase=has_ordered,
        **serializer.validated_data,
    )

    return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([permissions.IsAuthenticated])
def review_update(request, review_id):
    try:
        review = Review.objects.get(id=review_id, user=request.user)
    except Review.DoesNotExist:
        return Response(
            {"error": "Review not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = ReviewCreateSerializer(review, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(ReviewSerializer(review).data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def review_delete(request, review_id):
    try:
        review = Review.objects.get(id=review_id, user=request.user)
    except Review.DoesNotExist:
        return Response(
            {"error": "Review not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    review.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
