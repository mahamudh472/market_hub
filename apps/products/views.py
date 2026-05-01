from django.db.models import Count, Q
from rest_framework import generics, permissions, serializers
from rest_framework.response import Response

from .models import Product, Category, ProductReview
from .serializers import (
    ProductSerializer,
    SimpleProductSerializer,
    CategorySerializer,
    ProductReviewSerializer,
    VendorProductListSerializer,
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
    pagination_class = DefaultPagination

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

class PopularProductListView(generics.ListAPIView):
    """Top 10 popular products based on review count."""
    permission_classes = [permissions.AllowAny]
    serializer_class = SimpleProductSerializer

    def get_queryset(self):
        return (
            Product.objects
            .annotate(review_count=Count('reviews'))
            .order_by('-review_count', '-created_at')[:10]
            .select_related('vendor', 'category')
            .prefetch_related('images', 'reviews')
        )

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


class VendorProductListView(generics.ListAPIView):
    """
    GET /vendor/products/

    Returns the authenticated vendor's products with pagination, search, and
    category filter.

    Query params:
        search    (str) – filters on name, description, and category name
        category  (int) – category primary key
        page      (int) – page number (default 1)
        page_size (int) – items per page (default 10, max 100)

    The response includes a top-level `categories` key listing every distinct
    category that the vendor has products in (useful for the filter dropdown).
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VendorProductListSerializer
    pagination_class = DefaultPagination

    def _get_vendor(self):
        try:
            return self.request.user.vendor_profile
        except Exception:
            return None

    def get_queryset(self):
        vendor = self._get_vendor()
        if vendor is None:
            return Product.objects.none()

        qs = (
            Product.objects
            .filter(vendor=vendor)
            .select_related('category')
            .prefetch_related('images', 'variants')
            .annotate(variant_count_annotated=Count('variants', distinct=True))
            .order_by('-created_at')
        )

        # --- search ---
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(category__name__icontains=search)
            )

        # --- category filter ---
        category_id = self.request.query_params.get('category', '').strip()
        if category_id:
            qs = qs.filter(category_id=category_id)

        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        # Inject distinct categories for this vendor's products (unfiltered)
        vendor = self._get_vendor()
        if vendor is not None:
            categories = (
                Category.objects
                .filter(products__vendor=vendor)
                .distinct()
                .order_by('name')
                .values('id', 'name')
            )
            response.data['categories'] = list(categories)
        else:
            response.data['categories'] = []

        return response


# ─────────────────────────────────────────
# Plain category list (public)
# ─────────────────────────────────────────
class CategorySimpleListView(generics.ListAPIView):
    """
    GET /products/categories/simple/

    Returns all categories that have at least one product, as a flat list of
    {id, name} objects — suitable for filter dropdowns.
    """
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        categories = (
            Category.objects
            .filter(products__isnull=False)
            .distinct()
            .order_by('name')
            .values('id', 'name')
        )
        return Response(list(categories))

# class ReceviedProductListView(generics.ListAPIView):
#     """Products received by the authenticated vendor (i.e. orders that have been delivered to them)."""
#     permission_classes = [permissions.IsAuthenticated]
#     serializer_class = SimpleProductSerializer
#     pagination_class = DefaultPagination
#
#     def get_queryset(self):
#         vendor = self.request.user.vendor_profile
#         return (
#             Product.objects
#             .filter(orders__vendor=vendor, orders__status='delivered')
#             .select_related('vendor', 'category')
#             .prefetch_related('images', 'reviews')
#             .distinct()
#         )
