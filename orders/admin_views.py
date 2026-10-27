"""Staff-only endpoints used by the React admin portal."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Avg, Count, F, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from hooperzone.csv_export import csv_response
from products.models import Product

from .models import Order, OrderItem, ShopSettings
from .serializers import AdminOrderSerializer, ShopSettingsSerializer
from .services import maybe_cancel_unpaid_orders


class AdminPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def admin_stats(request):
    maybe_cancel_unpaid_orders()
    now = timezone.now()
    today = timezone.localdate()
    shop = ShopSettings.load()
    paid = Order.objects.filter(payment_status=Order.PAYMENT_STATUS_PAID)

    try:
        days = min(max(int(request.query_params.get("days", 7)), 1), 365)
    except ValueError:
        days = 7
    range_start = today - timedelta(days=days - 1)
    paid_in_range = paid.filter(created_at__date__gte=range_start)

    by_status = dict(Order.objects.values_list("status").annotate(n=Count("id")).values_list("status", "n"))

    daily = {
        row["day"]: row
        for row in paid_in_range.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(revenue=Sum("total"), orders=Count("id"))
    }
    series = []
    for offset in range(days):
        day = range_start + timedelta(days=offset)
        row = daily.get(day, {})
        series.append({"date": day.isoformat(), "revenue": row.get("revenue") or 0, "orders": row.get("orders") or 0})

    range_totals = paid_in_range.aggregate(revenue=Sum("total"), orders=Count("id"), aov=Avg("total"))
    best_sellers = (
        OrderItem.objects.filter(order__in=paid_in_range)
        .values("product_id", "product_name", "product__slug", "product__name_fa")
        .annotate(sold=Sum("quantity"), revenue=Sum(F("product_price") * F("quantity")))
        .order_by("-sold")[:5]
    )

    low_stock = Product.objects.filter(is_active=True, stock__lte=shop.low_stock_threshold).order_by("stock")[:8]
    recent = Order.objects.select_related("user").prefetch_related("items__product__images")[:6]

    return Response({
        "range_days": days,
        "revenue_range": range_totals["revenue"] or 0,
        "orders_range": range_totals["orders"] or 0,
        "average_order_value": round(range_totals["aov"] or 0),
        "revenue_total": paid.aggregate(v=Sum("total"))["v"] or 0,
        "revenue_30d": paid.filter(created_at__gte=now - timedelta(days=30)).aggregate(v=Sum("total"))["v"] or 0,
        "orders_total": Order.objects.count(),
        "orders_today": Order.objects.filter(created_at__date=today).count(),
        "awaiting_payment": Order.objects.filter(
            status=Order.STATUS_PENDING, payment_status__in=[Order.PAYMENT_STATUS_PENDING, Order.PAYMENT_STATUS_FAILED]
        ).count(),
        "to_ship": Order.objects.filter(
            status__in=[Order.STATUS_CONFIRMED, Order.STATUS_PROCESSING], payment_status=Order.PAYMENT_STATUS_PAID
        ).count(),
        "orders_by_status": by_status,
        "customers": get_user_model().objects.filter(is_staff=False, orders__isnull=False).distinct().count(),
        "products_active": Product.objects.filter(is_active=True).count(),
        "low_stock_threshold": shop.low_stock_threshold,
        # Kept under its old name for the dashboard chart.
        "last_7_days": series,
        "best_sellers": [
            {
                "slug": row["product__slug"],
                "name": row["product__name_fa"] or row["product_name"],
                "quantity": row["sold"],
                "revenue": row["revenue"],
            }
            for row in best_sellers
        ],
        "low_stock": [
            {"id": p.id, "slug": p.slug, "name": p.name_fa or p.name, "stock": p.stock} for p in low_stock
        ],
        "recent_orders": AdminOrderSerializer(recent, many=True).data,
    })


def filtered_orders(params):
    orders = Order.objects.select_related("user").prefetch_related("items__product__images")

    if params.get("status"):
        orders = orders.filter(status=params["status"])
    if params.get("payment_status"):
        orders = orders.filter(payment_status=params["payment_status"])
    if params.get("shipping_method"):
        orders = orders.filter(shipping_method=params["shipping_method"])

    date_from = parse_date(params.get("date_from") or "")
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    date_to = parse_date(params.get("date_to") or "")
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)

    search = (params.get("search") or "").strip()
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search)
            | Q(user__phone__icontains=search)
            | Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(shipping_phone__icontains=search)
            | Q(tracking_code__icontains=search)
        )
    return orders


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def admin_order_list(request):
    maybe_cancel_unpaid_orders()
    orders = filtered_orders(request.query_params)
    paginator = AdminPagination()
    page = paginator.paginate_queryset(orders, request)
    return paginator.get_paginated_response(AdminOrderSerializer(page, many=True).data)


def order_detail_response(order_number):
    order = (
        Order.objects.select_related("user").prefetch_related("items__product__images")
        .filter(order_number=order_number).first()
    )
    if not order:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(AdminOrderSerializer(order).data)


def apply_status(order, new_status):
    """Move `order` to `new_status`. Returns an error message, or None on success."""
    if new_status not in dict(Order.STATUS_CHOICES):
        return "Invalid status."
    if order.status == new_status:
        return None
    if order.status == Order.STATUS_CANCELLED:
        return "A cancelled order cannot be reopened."
    if not order.can_move_to(new_status):
        return "An order can only move forward."
    if new_status == Order.STATUS_CANCELLED:
        # Put the items back on the shelf, as a customer cancellation does.
        order.cancel(restock=True)
        return None
    order.status = new_status
    order.save(update_fields=["status", "updated_at"])
    return None


@api_view(["GET", "PATCH"])
@permission_classes([permissions.IsAdminUser])
@transaction.atomic
def admin_order_update(request, order_number):
    if request.method == "GET":
        return order_detail_response(order_number)
    try:
        order = Order.objects.select_for_update().get(order_number=order_number)
    except Order.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

    data = request.data
    if not any(k in data for k in ("status", "tracking_code", "payment_status", "notes")):
        return Response({"error": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)

    fields = []
    if "tracking_code" in data:
        order.tracking_code = str(data["tracking_code"] or "").strip()[:100]
        fields.append("tracking_code")
    if "notes" in data:
        order.notes = str(data["notes"] or "")
        fields.append("notes")
    if "payment_status" in data:
        if data["payment_status"] not in dict(Order.PAYMENT_STATUS_CHOICES):
            return Response({"error": "Invalid payment status."}, status=status.HTTP_400_BAD_REQUEST)
        order.payment_status = data["payment_status"]
        fields.append("payment_status")
    if fields:
        order.save(update_fields=fields + ["updated_at"])

    if "status" in data:
        error = apply_status(order, data["status"])
        if error:
            transaction.set_rollback(True)
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

    return Response(AdminOrderSerializer(order).data)


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def admin_order_bulk_status(request):
    numbers = request.data.get("order_numbers") or []
    new_status = request.data.get("status")
    if not isinstance(numbers, list) or not numbers:
        return Response({"error": "order_numbers is required."}, status=status.HTTP_400_BAD_REQUEST)
    if new_status not in dict(Order.STATUS_CHOICES):
        return Response({"error": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)

    updated, skipped = [], []
    for number in numbers[:200]:
        with transaction.atomic():
            order = Order.objects.select_for_update().filter(order_number=number).first()
            if not order:
                skipped.append({"order_number": number, "error": "Order not found."})
                continue
            error = apply_status(order, new_status)
            if error:
                skipped.append({"order_number": number, "error": error})
            else:
                updated.append(number)
    return Response({"updated": updated, "skipped": skipped})


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def admin_order_export(request):
    orders = filtered_orders(request.query_params)[:5000]
    header = [
        "order_number", "created_at", "status", "payment_status", "customer", "phone", "province", "city",
        "postal_code", "address", "shipping_method", "tracking_code", "items", "subtotal", "shipping_cost",
        "total", "payment_ref_id",
    ]
    rows = (
        [
            o.order_number,
            timezone.localtime(o.created_at).strftime("%Y-%m-%d %H:%M"),
            o.get_status_display(),
            o.get_payment_status_display(),
            o.user.get_full_name() or o.user.phone,
            o.shipping_phone,
            o.shipping_state,
            o.shipping_city,
            o.shipping_zip,
            o.shipping_address,
            o.get_shipping_method_display(),
            o.tracking_code,
            " | ".join(f"{i.product_name} x{i.quantity}" for i in o.items.all()),
            int(o.subtotal),
            int(o.shipping_cost),
            int(o.total),
            o.payment_ref_id,
        ]
        for o in orders
    )
    return csv_response("orders", header, rows)


@api_view(["GET", "PATCH"])
@permission_classes([permissions.IsAdminUser])
def admin_shop_settings(request):
    shop = ShopSettings.load()
    if request.method == "PATCH":
        serializer = ShopSettingsSerializer(shop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    return Response(ShopSettingsSerializer(shop).data)
