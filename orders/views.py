import uuid
from decimal import Decimal
from urllib.parse import urlparse

from django.conf import settings
from django.db import transaction
from django.http.request import validate_host
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from cart.models import Cart
from products.models import Product

from .models import Order, OrderItem, ShopSettings
from .serializers import OrderCreateSerializer, OrderSerializer, ShopInfoSerializer
from .services import maybe_cancel_unpaid_orders


def is_allowed_callback(url, request):
    """The gateway sends the customer back here, so it must be one of our own hosts."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    allowed = list(settings.ALLOWED_HOSTS) + [request.get_host().split(":")[0]]
    return validate_host(parsed.hostname, allowed)


def generate_order_number():
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def shipping_methods(request):
    return Response(ShopSettings.load().shipping_methods())


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def shop_info(request):
    """Public store contact details and trust badges for the footer and contact page."""
    return Response(ShopInfoSerializer(ShopSettings.load()).data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def order_list(request):
    maybe_cancel_unpaid_orders()
    orders = Order.objects.filter(user=request.user).prefetch_related("items__product__images")
    return Response(OrderSerializer(orders, many=True).data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def order_detail(request, order_number):
    try:
        order = Order.objects.get(order_number=order_number, user=request.user)
    except Order.DoesNotExist:
        return Response(
            {"error": "Order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic
def order_create(request):
    serializer = OrderCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        return Response(
            {"error": "Your cart is empty."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    cart_items = list(cart.items.select_related("product"))
    if not cart_items:
        return Response(
            {"error": "Your cart is empty."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Lock the product rows so concurrent checkouts can't both pass the stock
    # check and oversell.
    products = Product.objects.select_for_update().in_bulk([item.product_id for item in cart_items])
    for item in cart_items:
        item.product = products[item.product_id]

    for item in cart_items:
        if not item.product.is_active:
            return Response(
                {"error": f"{item.product.name} is no longer available."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if item.quantity > item.product.stock:
            return Response(
                {
                    "error": f"Insufficient stock for {item.product.name}. "
                    f"Available: {item.product.stock}, Requested: {item.quantity}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    subtotal = sum(item.subtotal for item in cart_items)
    shipping_cost = Decimal(ShopSettings.load().shipping_fee(serializer.validated_data["shipping_method"]))
    total = subtotal + shipping_cost

    order = Order.objects.create(
        user=request.user,
        order_number=generate_order_number(),
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        total=total,
        **serializer.validated_data,
    )

    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            product_name=item.product.name,
            product_price=item.product.effective_price,
            quantity=item.quantity,
        )
        item.product.stock -= item.quantity
        item.product.save(update_fields=["stock"])

    cart.items.all().delete()
    transaction.on_commit(maybe_cancel_unpaid_orders)

    return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic
def order_cancel(request, order_number):
    try:
        order = Order.objects.select_for_update().get(order_number=order_number, user=request.user)
    except Order.DoesNotExist:
        return Response(
            {"error": "Order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if order.status not in [Order.STATUS_PENDING, Order.STATUS_CONFIRMED]:
        return Response(
            {"error": "This order cannot be cancelled."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    order.cancel(restock=True)

    return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def order_pay_initiate(request, order_number):
    try:
        order = Order.objects.get(order_number=order_number, user=request.user)
    except Order.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

    if order.payment_status == Order.PAYMENT_STATUS_PAID:
        return Response({"error": "This order is already paid."}, status=status.HTTP_400_BAD_REQUEST)

    if order.status == Order.STATUS_CANCELLED:
        return Response({"error": "This order has been cancelled."}, status=status.HTTP_400_BAD_REQUEST)

    gateway_name = str(request.data.get("gateway", "zarinpal")).lower()
    if gateway_name not in ("zarinpal", "idpay"):
        return Response({"error": "Unsupported payment gateway."}, status=status.HTTP_400_BAD_REQUEST)

    # Where the gateway returns the customer: the storefront's payment result page.
    callback_url = request.data.get("callback_url") or request.build_absolute_uri(
        f"/payment/result?order_number={order.order_number}&gateway={gateway_name}"
    )
    if not is_allowed_callback(callback_url, request):
        return Response({"error": "Invalid callback_url."}, status=status.HTTP_400_BAD_REQUEST)

    from .payments import PaymentGatewayError, get_payment_gateway

    gateway = get_payment_gateway(gateway_name)
    try:
        payment_data = gateway.request_payment(order, callback_url)
    except PaymentGatewayError:
        return Response(
            {"error": "Payment gateway is unavailable. Please try again later."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # Remember which transaction belongs to this order so the (public) verify
    # endpoint can't be fed an arbitrary authority.
    order.payment_gateway = gateway_name
    order.payment_authority = payment_data.get("authority") or payment_data.get("id") or ""
    order.save(update_fields=["payment_gateway", "payment_authority"])

    return Response(
        {
            "order_number": order.order_number,
            "gateway": gateway_name,
            **payment_data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST", "GET"])
@permission_classes([permissions.AllowAny])
@transaction.atomic
def order_pay_verify(request):
    data = request.data if request.method == "POST" else request.query_params
    order_number = data.get("order_number")
    authority = data.get("Authority") or data.get("authority") or data.get("id")

    if not order_number or not authority:
        return Response(
            {"error": "Missing order_number or payment authority."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        order = Order.objects.select_for_update().get(order_number=order_number)
    except Order.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

    if order.payment_status == Order.PAYMENT_STATUS_PAID:
        return Response(
            {"message": "Order already paid.", "order": OrderSerializer(order).data},
            status=status.HTTP_200_OK,
        )

    if not order.payment_authority or str(authority) != order.payment_authority:
        return Response(
            {"success": False, "error": "Payment authority does not match this order."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if order.status == Order.STATUS_CANCELLED:
        return Response(
            {"success": False, "error": "This order has been cancelled."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ZarinPal returns Status=NOK when the customer cancelled or the bank declined:
    # there is nothing to verify.
    callback_status = str(data.get("Status") or data.get("status") or "")
    if order.payment_gateway == "zarinpal" and callback_status.upper() == "NOK":
        order.payment_status = Order.PAYMENT_STATUS_FAILED
        order.save(update_fields=["payment_status", "updated_at"])
        return Response(
            {"success": False, "error": "Payment was cancelled or declined."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from .payments import get_payment_gateway

    gateway = get_payment_gateway(order.payment_gateway)
    verification = gateway.verify_payment(order, authority)

    if verification.get("success"):
        order.payment_status = Order.PAYMENT_STATUS_PAID
        order.status = Order.STATUS_CONFIRMED
        order.payment_ref_id = str(verification.get("ref_id") or verification.get("track_id") or "")[:100]
        order.payment_card_pan = str(verification.get("card_pan") or "")[:30]
        order.paid_at = timezone.now()
        order.save(update_fields=[
            "payment_status", "status", "payment_ref_id", "payment_card_pan", "paid_at", "updated_at",
        ])
        return Response(
            {
                "success": True,
                "message": "Payment successful and verified.",
                "ref_id": order.payment_ref_id,
                "order": OrderSerializer(order).data,
            },
            status=status.HTTP_200_OK,
        )

    order.payment_status = Order.PAYMENT_STATUS_FAILED
    order.save(update_fields=["payment_status", "updated_at"])
    return Response(
        {
            "success": False,
            "error": "Payment verification failed.",
        },
        status=status.HTTP_400_BAD_REQUEST,
    )
