"""Order housekeeping shared by views, the admin API and management commands."""
import logging
from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .models import Order, ShopSettings

logger = logging.getLogger(__name__)

SWEEP_CACHE_KEY = "orders:unpaid-sweep"
SWEEP_INTERVAL_SECONDS = 300


def cancel_unpaid_orders(timeout_minutes=None):
    """Cancel pending, unpaid orders older than the timeout and release their stock. Returns the count."""
    if timeout_minutes is None:
        timeout_minutes = ShopSettings.load().unpaid_order_timeout_minutes
    if not timeout_minutes:
        return 0
    cutoff = timezone.now() - timedelta(minutes=timeout_minutes)
    stale = Order.objects.filter(
        status=Order.STATUS_PENDING,
        payment_status__in=[Order.PAYMENT_STATUS_PENDING, Order.PAYMENT_STATUS_FAILED],
        created_at__lt=cutoff,
    ).values_list("pk", flat=True)

    cancelled = 0
    for pk in list(stale):
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=pk)
            # Re-check under the lock: the customer may have just paid.
            if order.status == Order.STATUS_PENDING and order.payment_status != Order.PAYMENT_STATUS_PAID:
                order.cancel(restock=True)
                cancelled += 1
    if cancelled:
        logger.info("Cancelled %s unpaid orders older than %s minutes", cancelled, timeout_minutes)
    return cancelled


def maybe_cancel_unpaid_orders():
    """Run the unpaid-order sweep at most every few minutes (the host has no cron)."""
    if not cache.add(SWEEP_CACHE_KEY, True, SWEEP_INTERVAL_SECONDS):
        return 0
    try:
        return cancel_unpaid_orders()
    except Exception:  # housekeeping must never break the request that triggered it
        logger.exception("Unpaid order sweep failed")
        return 0
