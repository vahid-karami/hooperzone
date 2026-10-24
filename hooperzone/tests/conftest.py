import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache():
    # Throttle counters live in the cache; don't let them leak between tests.
    cache.clear()
    yield
    cache.clear()
