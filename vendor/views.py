from django.db.models import Count
from rest_framework import generics, permissions
from rest_framework.response import Response

from .models import VendorProfile
from .serializers import VendorDetailSerializer
from products.models import Product, Category
from products.serializers import SimpleProductSerializer, CategorySerializer


class StoreDetailView(generics.RetrieveAPIView):
    """
    Public store page — returns vendor profile + paginated product list.
    Supports ?category=<slug> filter on the product list.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = VendorDetailSerializer
    lookup_field = 'slug'
    queryset = VendorProfile.objects.filter(is_active=True)

    def retrieve(self, request, *args, **kwargs):
        vendor = self.get_object()
        vendor_data = self.get_serializer(vendor).data

        # --- Products ---
        products_qs = (
            Product.objects
            .filter(vendor=vendor)
            .select_related('category', 'vendor')
            .prefetch_related('images', 'reviews')
        )

        category_slug = request.query_params.get('category')
        if category_slug:
            products_qs = products_qs.filter(category__slug=category_slug)

        # simple sort
        sort = request.query_params.get('sort', '-created_at')
        allowed_sorts = ['price', '-price', '-created_at', 'created_at']
        if sort in allowed_sorts:
            products_qs = products_qs.order_by(sort)

        products_data = SimpleProductSerializer(
            products_qs, many=True, context={'request': request}
        ).data

        # --- Categories available in this store ---
        store_categories = (
            Category.objects
            .filter(products__vendor=vendor)
            .annotate(product_count=Count('products'))
            .distinct()
        )
        categories_data = CategorySerializer(
            store_categories, many=True, context={'request': request}
        ).data

        return Response({
            'vendor': vendor_data,
            'categories': categories_data,
            'products': products_data,
        })
