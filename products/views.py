from django.db.models import Count, Q
from rest_framework import generics, permissions, serializers
from rest_framework.response import Response

from .models import Product, Category, ProductReview
from .serializers import (
    ProductSerializer,
    SimpleProductSerializer,
    CategorySerializer,
    ProductReviewSerializer,
)
from .paginations import DefaultPagination
from rest_framework import status


class CategoryListView(generics.ListAPIView):
    """All active top-level categories with product counts."""
    permission_classes = [permissions.AllowAny]
    serializer_class = CategorySerializer

    def get_queryset(self):
        return (
            Category.objects
            .filter(parent__isnull=True)
            .annotate(product_count=Count('products'))
            .order_by('name')
        )


class CategoryProductListView(generics.ListAPIView):
    """Products filtered by a category slug (includes sub-categories)."""
    permission_classes = [permissions.AllowAny]
    serializer_class = SimpleProductSerializer

    def get_queryset(self):
        slug = self.kwargs['slug']
        category = generics.get_object_or_404(Category, slug=slug)
        # include all descendant categories via a recursive-like approach (2 levels deep is common)
        descendant_ids = list(
            Category.objects.filter(parent=category).values_list('id', flat=True)
        )
        category_ids = [category.id] + descendant_ids

        qs = (
            Product.objects
            .filter(category_id__in=category_ids)
            .select_related('vendor', 'category')
            .prefetch_related('images', 'reviews')
            .annotate(product_count=Count('reviews'))
        )

        # optional filters via query params
        vendor_id = self.request.query_params.get('vendor')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        sort = self.request.query_params.get('sort', '-created_at')

        if vendor_id:
            qs = qs.filter(vendor_id=vendor_id)
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)

        allowed_sorts = ['price', '-price', '-created_at', 'created_at', '-product_count']
        if sort in allowed_sorts:
            qs = qs.order_by(sort)

        return qs


class ProductSearchView(generics.ListAPIView):
    """Full-text product search via ?q=<query>"""
    permission_classes = [permissions.AllowAny]
    serializer_class = SimpleProductSerializer

    def get_queryset(self):
        query = self.request.query_params.get('q', '').strip()
        if not query:
            return Product.objects.none()
        return (
            Product.objects
            .filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(category__name__icontains=query) |
                Q(vendor__name__icontains=query)
            )
            .select_related('vendor', 'category')
            .prefetch_related('images', 'reviews')
            .distinct()
        )


class ProductDetailView(generics.RetrieveAPIView):
    """Full product detail — includes variants, images, aggregated rating."""
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductSerializer
    lookup_field = 'pk'

    def get_queryset(self):
        return (
            Product.objects
            .select_related('vendor', 'category')
            .prefetch_related(
                'images',
                'variant_types__options',
                'variants__options__variant_type',
                'reviews',
            )
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data

        # Related products (same category, excluding self)
        related = (
            Product.objects
            .filter(category=instance.category)
            .exclude(pk=instance.pk)
            .select_related('vendor')
            .prefetch_related('images', 'reviews')[:8]
        )
        data['related_products'] = SimpleProductSerializer(
            related, many=True, context=self.get_serializer_context()
        ).data

        # "You may also like" — products from same vendor, different category
        also_like = (
            Product.objects
            .filter(vendor=instance.vendor)
            .exclude(pk=instance.pk)
            .exclude(category=instance.category)
            .select_related('vendor')
            .prefetch_related('images', 'reviews')[:8]
        )
        data['you_may_also_like'] = SimpleProductSerializer(
            also_like, many=True, context=self.get_serializer_context()
        ).data

        # Dummy delivery charge
        data['delivery_info'] = {
            'standard': {'label': 'Standard Delivery', 'days': '5-7', 'charge': 60},
            'express': {'label': 'Express Delivery', 'days': '1-2', 'charge': 150},
            'note': 'Free delivery on orders above ৳500',
        }

        return Response(data)


# ─────────────────────────────────────────
# Reviews (separate endpoint)
# ─────────────────────────────────────────
class ProductReviewListView(generics.ListAPIView):
    """Paginated reviews for a given product."""
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductReviewSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        product_id = self.kwargs['product_id']
        return (
            ProductReview.objects
            .filter(product_id=product_id)
            .select_related('user')
            .prefetch_related('images')
            .order_by('-created_at')
        )


class ProductReviewCreateView(generics.CreateAPIView):
    """Authenticated user submits a review (with optional images)."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductReviewSerializer

    def get_queryset(self):
        return ProductReview.objects.all()

    def perform_create(self, serializer):
        product_id = self.kwargs['product_id']
        product = generics.get_object_or_404(Product, pk=product_id)

        # One review per user per product
        if ProductReview.objects.filter(product=product, user=self.request.user).exists():
            raise serializers.ValidationError("You have already reviewed this product.")

        serializer.save(user=self.request.user, product=product)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)

        return Response(
            {"message": "Review submitted successfully."},
            status=status.HTTP_201_CREATED
        )

