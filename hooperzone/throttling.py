"""Throttles keyed on the real visitor IP.

On ParsPack the app sits behind one ingress proxy. Waitress (server_start.serve) takes the last
X-Forwarded-For entry, which that proxy wrote, as REMOTE_ADDR, so a forged header can't fake an IP.
CF-Connecting-IP is only trusted when Cloudflare proxies the site (TRUST_CF_CONNECTING_IP=True);
otherwise anyone could send it and get a fresh limit with every request.
"""
from django.conf import settings
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle


def client_ip(request):
    if getattr(settings, "TRUST_CF_CONNECTING_IP", False):
        cf_ip = request.META.get("HTTP_CF_CONNECTING_IP")
        if cf_ip:
            return cf_ip
    return request.META.get("REMOTE_ADDR")


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
