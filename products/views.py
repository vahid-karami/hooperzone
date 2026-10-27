from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count, F, Q
from django.utils import timezone
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from hooperzone.csv_export import csv_response

from .models import Category, Product, ProductImage, Sport
from .serializers import (
    CategoryAdminSerializer,
    CategorySerializer,
    ProductImageSerializer,
    SportSerializer,
    ProductAdminSerializer,
    ProductCreateSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True).annotate(
        active_product_count=Count("products", filter=Q(products__is_active=True))
    ).order_by("name")
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_serializer(self, *args, **kwargs):
        lang = self.request.query_params.get('lang', 'en')
        kwargs.setdefault('context', {})
        kwargs['context']['lang'] = lang
        return super().get_serializer(*args, **kwargs)


class SportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sport.objects.filter(is_active=True)
    serializer_class = SportSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    pagination_class = None

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["lang"] = self.request.query_params.get("lang", "en")
        return context


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.filter(is_active=True).select_related("category").prefetch_related("images")
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "brand"]
    ordering_fields = ["price", "created_at", "name"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer

    def get_serializer(self, *args, **kwargs):
        lang = self.request.query_params.get('lang', 'en')
        kwargs.setdefault('context', {})
        kwargs['context']['lang'] = lang
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()

        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category__slug=category)

        injury_type = self.request.query_params.get("injury_type")
        if injury_type:
            queryset = queryset.filter(injury_type=injury_type)

        sport = self.request.query_params.get("sport")
        if sport:
            queryset = queryset.filter(sports__slug=sport).distinct()

        brand = self.request.query_params.get("brand")
        if brand:
            queryset = queryset.filter(brand__icontains=brand)

        size = self.request.query_params.get("size")
        if size:
            queryset = queryset.filter(size__iexact=size)

        min_price = self.request.query_params.get("min_price")
        if min_price:
            queryset = queryset.filter(price__gte=min_price)

        max_price = self.request.query_params.get("max_price")
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        in_stock = self.request.query_params.get("in_stock")
        if in_stock == "true":
            queryset = queryset.filter(stock__gt=0)

        on_sale = self.request.query_params.get("on_sale")
        if on_sale == "true":
            queryset = queryset.filter(discount_price__isnull=False, discount_price__lt=F("price"))

        is_featured = self.request.query_params.get("is_featured")
        if is_featured == "true":
            queryset = queryset.filter(is_featured=True)

        return queryset

    @action(detail=False, methods=["get"])
    def featured(self, request):
        featured = self.get_queryset().filter(is_featured=True)
        lang = self.request.query_params.get('lang', 'en')
        page = self.paginate_queryset(featured)
        if page is not None:
            serializer = ProductListSerializer(page, many=True, context={'lang': lang})
            return self.get_paginated_response(serializer.data)
        serializer = ProductListSerializer(featured, many=True, context={'lang': lang})
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def injury_types(self, request):
        return Response(dict(Product.INJURY_TYPE_CHOICES))


class AdminPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


class CategoryAdminViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.annotate(product_count=Count("products")).order_by("name")
    serializer_class = CategoryAdminSerializer
    permission_classes = [permissions.IsAdminUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = "slug"
    pagination_class = None

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        if category.products.exists():
            return Response(
                {"error": "This category still has products. Move or delete them first, or deactivate it."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class ProductAdminViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().select_related("category").prefetch_related("images")
    permission_classes = [permissions.IsAdminUser]
    pagination_class = AdminPagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    lookup_field = "slug"
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "name_fa", "description", "brand", "injury_type", "slug"]
    ordering_fields = ["price", "created_at", "name", "stock"]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return ProductCreateSerializer
        return ProductAdminSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        is_featured = self.request.query_params.get("is_featured")
        if is_featured is not None:
            queryset = queryset.filter(is_featured=is_featured.lower() == "true")

        in_stock = self.request.query_params.get("in_stock")
        if in_stock is not None:
            if in_stock.lower() == "true":
                queryset = queryset.filter(stock__gt=0)
            else:
                queryset = queryset.filter(stock__lte=0)

        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category__slug=category)

        low_stock = self.request.query_params.get("low_stock")
        if low_stock == "true":
            from orders.models import ShopSettings

            queryset = queryset.filter(stock__lte=ShopSettings.load().low_stock_threshold)

        return queryset

    def _admin_data(self, product):
        product = self.get_queryset().get(pk=product.pk)
        return ProductAdminSerializer(product, context=self.get_serializer_context()).data

    def create(self, request, *args, **kwargs):
        serializer = ProductCreateSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(self._admin_data(product), status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        serializer = ProductCreateSerializer(
            self.get_object(), data=request.data, partial=partial, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(self._admin_data(product))

    def _image_list(self, product):
        # Fresh query: get_object() prefetched the images before this request changed them.
        images = ProductImage.objects.filter(product=product).order_by("-is_primary", "-created_at")
        return ProductImageSerializer(images, many=True).data

    @action(detail=True, methods=["get", "post"], url_path="images", parser_classes=[MultiPartParser, FormParser])
    def images(self, request, slug=None):
        """List a product's images, or upload one (multipart field `image`, optional `alt_text`, `is_primary`)."""
        product = self.get_object()
        if request.method == "POST":
            upload = request.FILES.get("image")
            if not upload:
                return Response({"error": "Choose an image to upload."}, status=status.HTTP_400_BAD_REQUEST)
            serializer = ProductImageSerializer(data={
                "image": upload,
                "alt_text": request.data.get("alt_text", "") or product.name_fa or product.name,
            })
            serializer.is_valid(raise_exception=True)
            existing = ProductImage.objects.filter(product=product)
            make_primary = str(request.data.get("is_primary", "")).lower() == "true" or not existing.exists()
            with transaction.atomic():
                if make_primary:
                    existing.update(is_primary=False)
                serializer.save(product=product, is_primary=make_primary)
            Product.objects.filter(pk=product.pk).update(updated_at=timezone.now())
        return Response(self._image_list(product))

    @action(detail=True, methods=["patch", "delete"], url_path=r"images/(?P<image_id>\d+)")
    def image_detail(self, request, slug=None, image_id=None):
        """Set an image as primary, change its alt text, or delete it."""
        product = self.get_object()
        image = ProductImage.objects.filter(product=product, pk=image_id).first()
        if not image:
            return Response({"error": "Image not found."}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            if request.method == "DELETE":
                was_primary = image.is_primary
                image.image.delete(save=False)
                image.delete()
                if was_primary:
                    first = ProductImage.objects.filter(product=product).order_by("-created_at").first()
                    if first:
                        first.is_primary = True
                        first.save(update_fields=["is_primary"])
            else:
                if "alt_text" in request.data:
                    image.alt_text = str(request.data["alt_text"])[:200]
                if str(request.data.get("is_primary", "")).lower() == "true":
                    ProductImage.objects.filter(product=product).exclude(pk=image.pk).update(is_primary=False)
                    image.is_primary = True
                image.save()
        return Response(self._image_list(product))

    @action(detail=False, methods=["post"])
    def bulk_action(self, request):
        """Apply one action (activate, deactivate, feature, unfeature, delete) to several products."""
        slugs = request.data.get("slugs") or []
        action_name = request.data.get("action")
        if not isinstance(slugs, list) or not slugs:
            return Response({"error": "slugs is required."}, status=status.HTTP_400_BAD_REQUEST)
        products = Product.objects.filter(slug__in=slugs)
        updates = {
            "activate": {"is_active": True},
            "deactivate": {"is_active": False},
            "feature": {"is_featured": True},
            "unfeature": {"is_featured": False},
        }
        if action_name in updates:
            count = products.update(**updates[action_name])
        elif action_name == "delete":
            from orders.models import OrderItem

            # Products that were ordered stay for the order history; deactivate those instead.
            ordered = set(OrderItem.objects.filter(product__in=products).values_list("product_id", flat=True))
            count = products.filter(pk__in=ordered).update(is_active=False)
            for product in products.exclude(pk__in=ordered):
                for image in product.images.all():
                    image.image.delete(save=False)
                product.delete()
                count += 1
        else:
            return Response({"error": "Unknown action."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"updated_count": count})

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        products = self.filter_queryset(self.get_queryset()).prefetch_related("sports")
        header = [
            "slug", "name", "name_fa", "category", "brand", "price", "discount_price", "cost", "stock",
            "injury_type", "size", "color", "material", "is_active", "is_featured", "sports",
        ]
        rows = (
            [
                p.slug, p.name, p.name_fa, p.category.name_fa or p.category.name, p.brand,
                int(p.price), int(p.discount_price) if p.discount_price else "", int(p.cost) if p.cost else "",
                p.stock, p.get_injury_type_display(), p.size, p.color, p.material,
                "yes" if p.is_active else "no", "yes" if p.is_featured else "no",
                ", ".join(s.name_fa or s.name for s in p.sports.all()),
            ]
            for p in products
        )
        return csv_response("products", header, rows)

    @action(detail=False, methods=["post"])
    def bulk_price_update(self, request):
        category_id = request.data.get("category_id")
        percentage = request.data.get("percentage")
        
        if percentage is None:
            return Response({"error": "Percentage is required"}, status=400)
            
        try:
            percentage = Decimal(str(percentage))
        except (InvalidOperation, ValueError, TypeError):
            return Response({"error": "Invalid percentage format"}, status=400)

        if not percentage.is_finite() or percentage <= -100:
            return Response({"error": "Percentage must be a number greater than -100"}, status=400)

        if category_id:
            try:
                category_id = int(category_id)
            except (ValueError, TypeError):
                return Response({"error": "Invalid category_id"}, status=400)

        queryset = self.get_queryset()
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        factor = 1 + percentage / 100

        def adjust(amount):
            new_amount = amount * factor
            # Round to nearest 1000 Toman for clean pricing, but never round a
            # small price down to zero.
            rounded = (new_amount / 1000).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * 1000
            return rounded if rounded > 0 else new_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        with transaction.atomic():
            products = list(queryset.select_for_update())
            for product in products:
                if product.price:
                    product.price = adjust(product.price)
                if product.discount_price:
                    product.discount_price = adjust(product.discount_price)
            Product.objects.bulk_update(products, ["price", "discount_price"], batch_size=200)
            updated_count = len(products)

        return Response({"message": f"Successfully updated {updated_count} products", "updated_count": updated_count})
