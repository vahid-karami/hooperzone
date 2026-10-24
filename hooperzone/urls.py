from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve
from rest_framework_simplejwt.views import TokenRefreshView


def api_root(request):
    return JsonResponse({
        "message": "HooperZone API",
        "version": "1.0",
        "endpoints": {
            "admin": "/admin/",
            "auth": "/api/auth/",
            "products": "/api/products/",
            "cart": "/api/cart/",
            "orders": "/api/orders/",
            "reviews": "/api/reviews/",
            "favorites": "/api/favorites/",
        },
    })


def frontend_app(request):
    """Serve the built React app for every non-API URL (client-side routing).

    Falls back to the API index when the frontend hasn't been built (local backend-only dev).
    """
    index = settings.FRONTEND_DIST / "index.html"
    if not index.exists():
        return api_root(request)
    response = HttpResponse(index.read_text(encoding="utf-8"))
    response["Cache-Control"] = "no-cache"
    return response


urlpatterns = [
    path("api/", api_root, name="api-root"),
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/products/", include("products.urls")),
    path("api/cart/", include("cart.urls")),
    path("api/orders/", include("orders.urls")),
    path("api/reviews/", include("reviews.urls")),
    path("api/favorites/", include("favorites.urls")),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif getattr(settings, "SERVE_MEDIA", False):
    # Production without a separate web server (Wispbyte): Django serves uploaded images.
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]

urlpatterns += [
    re_path(r"^(?!api/|admin/|media/|static/).*$", frontend_app, name="frontend"),
]
