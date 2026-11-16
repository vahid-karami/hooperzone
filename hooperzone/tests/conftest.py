import pytest
from django.core.cache import caches


@pytest.fixture(autouse=True)
def _clear_cache():
    # Throttle counters and rendered pages live in the caches; don't let them leak between tests.
    for cache in caches.all():
        cache.clear()
    yield
    for cache in caches.all():
        cache.clear()
