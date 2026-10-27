"""Throttles that see the real visitor IP behind Cloudflare."""
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle


def client_ip(request):
    """Cloudflare puts the visitor's address in CF-Connecting-IP; REMOTE_ADDR is its edge server."""
    return request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR")


class ClientIPMixin:
    def get_ident(self, request):
        return client_ip(request) or super().get_ident(request)


class IPRateThrottle(ClientIPMixin, SimpleRateThrottle):
    """Per-IP limit for anonymous endpoints. Subclasses set `scope`."""

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class AuthRateThrottle(IPRateThrottle):
    """Password login and registration: stops password guessing."""

    scope = "auth"


class ClientIPScopedRateThrottle(ClientIPMixin, ScopedRateThrottle):
    pass
