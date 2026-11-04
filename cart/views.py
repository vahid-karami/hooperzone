from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from products.models import Product, ProductSize

from .models import Cart, CartItem
from .serializers import CartSerializer


def parse_quantity(value):
    """Return value as an int, or None if it isn't a whole number."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def cart_detail(request):
    cart = get_or_create_cart(request.user)
    return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def cart_add_item(request):
    cart = get_or_create_cart(request.user)

    product_id = request.data.get("product_id")
    quantity = parse_quantity(request.data.get("quantity", 1))

    if not product_id:
        return Response(
            {"error": "product_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if quantity is None or quantity < 1:
        return Response(
            {"error": "quantity must be a positive integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        product = Product.objects.get(id=product_id, is_active=True)
    except (Product.DoesNotExist, ValueError, TypeError):
        return Response(
            {"error": "Product not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    size, error = resolve_size(product, request.data.get("size_id"))
    if error:
        return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
    available = size.stock if size else product.stock

    if available < quantity:
        return Response(
            {"error": f"Only {available} items available in stock."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        size=size,
        defaults={"quantity": quantity},
    )

    if not created:
        new_quantity = cart_item.quantity + quantity
        if available < new_quantity:
            return Response(
                {"error": f"Only {available} items available in stock."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cart_item.quantity = new_quantity
        cart_item.save()

    return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


def resolve_size(product, size_id):
    """(size, error). A product with sizes needs one of its active sizes; one without takes none."""
    sizes = ProductSize.objects.filter(product=product, is_active=True)
    if not sizes.exists():
        return (None, "This product has no sizes.") if size_id else (None, None)
    if not size_id:
        return None, "Please choose a size."
    try:
        return sizes.get(pk=size_id), None
    except (ProductSize.DoesNotExist, ValueError, TypeError):
        return None, "This size is not available."


@api_view(["PATCH"])
@permission_classes([permissions.IsAuthenticated])
def cart_update_item(request):
    cart = get_or_create_cart(request.user)

    item_id = request.data.get("item_id")
    quantity = request.data.get("quantity")

    if not item_id or quantity is None:
        return Response(
            {"error": "item_id and quantity are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        cart_item = CartItem.objects.get(id=item_id, cart=cart)
    except (CartItem.DoesNotExist, ValueError, TypeError):
        return Response(
            {"error": "Cart item not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    quantity = parse_quantity(quantity)
    if quantity is None:
        return Response(
            {"error": "quantity must be an integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if quantity <= 0:
        cart_item.delete()
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)

    if cart_item.available_stock < quantity:
        return Response(
            {"error": f"Only {cart_item.available_stock} items available in stock."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    cart_item.quantity = quantity
    cart_item.save()

    return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def cart_remove_item(request):
    cart = get_or_create_cart(request.user)

    item_id = request.data.get("item_id")
    if not item_id:
        return Response(
            {"error": "item_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        cart_item = CartItem.objects.get(id=item_id, cart=cart)
    except (CartItem.DoesNotExist, ValueError, TypeError):
        return Response(
            {"error": "Cart item not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    cart_item.delete()
    return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def cart_clear(request):
    cart = get_or_create_cart(request.user)
    cart.items.all().delete()
    return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)
