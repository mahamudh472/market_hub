from django.db.models import Count
from rest_framework import generics, permissions
from rest_framework.response import Response

from .models import VendorProfile
from .serializers import VendorDetailSerializer
from products.models import Product, Category
from products.serializers import SimpleProductSerializer, CategorySerializer
from .paginations import StandardResultsSetPagination
from accounts.permissions import IsVendorOwner
from rest_framework.exceptions import NotFound


class StoreListView(generics.ListAPIView):
    """
    List of all active stores. Returns basic info + avg rating.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = VendorDetailSerializer
    pagination_class = StandardResultsSetPagination
    queryset = VendorProfile.objects.filter(is_active=True).order_by('-created_at')


class StoreDetailView(generics.RetrieveAPIView):
    """
    Public store page — returns vendor profile + paginated product list.
    Supports ?category=<slug> filter on the product list.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = VendorDetailSerializer
    lookup_field = 'slug'
    queryset = VendorProfile.objects.filter(is_active=True)

    def get_permissions(self):
        if self.kwargs.get('slug') is None:
            return [IsVendorOwner()]
        return super().get_permissions()

    def get_object(self):
        slug = self.kwargs.get('slug')
        try:
            if slug:
                return VendorProfile.objects.get(slug=slug, is_active=True)
            else:
                # If no slug provided, return the vendor profile of the authenticated user
                return self.request.user.vendor_profile
        except VendorProfile.DoesNotExist:
            raise NotFound("Vendor not found.")

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
