"""Staff-only customer list for the admin portal."""
from django.contrib.auth import get_user_model
from django.db.models import Count, Max, Q, Sum
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination

from hooperzone.csv_export import csv_response

User = get_user_model()

SORTS = {
    "recent": "-date_joined",
    "spent": "-total_spent",
    "orders": "-order_count",
    "last_order": "-last_order_at",
}


class CustomerPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


def customer_queryset(params):
    paid = Q(orders__payment_status="paid")
    users = User.objects.filter(is_staff=False).annotate(
        order_count=Count("orders", distinct=True),
        paid_order_count=Count("orders", filter=paid, distinct=True),
        total_spent=Sum("orders__total", filter=paid),
        last_order_at=Max("orders__created_at"),
    )
    search = (params.get("search") or "").strip()
    if search:
        users = users.filter(
            Q(phone__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search)
            | Q(email__icontains=search) | Q(username__icontains=search)
        )
    if params.get("has_orders") == "true":
        users = users.filter(order_count__gt=0)
    return users.order_by(SORTS.get(params.get("sort"), "-date_joined"), "-id")


def serialize(user):
    return {
        "id": user.id,
        "name": user.get_full_name(),
        "phone": user.phone,
        "email": user.email,
        "city": getattr(user, "city", ""),
        "province": getattr(user, "province", ""),
        "is_verified": user.is_verified,
        "date_joined": user.date_joined,
        "order_count": user.order_count,
        "paid_order_count": user.paid_order_count,
        "total_spent": user.total_spent or 0,
        "last_order_at": user.last_order_at,
    }


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def customer_list(request):
    paginator = CustomerPagination()
    page = paginator.paginate_queryset(customer_queryset(request.query_params), request)
    return paginator.get_paginated_response([serialize(u) for u in page])


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def customer_export(request):
    def fmt(dt):
        return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M") if dt else ""

    header = ["name", "phone", "email", "province", "city", "joined", "orders", "paid_orders", "total_spent", "last_order"]
    rows = (
        [
            u.get_full_name(), u.phone, u.email, getattr(u, "province", ""), getattr(u, "city", ""),
            fmt(u.date_joined), u.order_count, u.paid_order_count, int(u.total_spent or 0), fmt(u.last_order_at),
        ]
        for u in customer_queryset(request.query_params)
    )
    return csv_response("customers", header, rows)
