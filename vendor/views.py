from django.db.models import Count
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.utils import timezone

from .models import VendorProfile
from .serializers import (
    VendorDetailSerializer,
    VendorProfileSubmissionSerializer,
    SimpleVendorProfileSerializer,
    ProductCreateSerializer,
)
from products.models import Product, Category
from products.serializers import SimpleProductSerializer, CategorySerializer
from .paginations import StandardResultsSetPagination
from accounts.permissions import IsVendorOwner
from rest_framework.exceptions import NotFound


def _pending_vendor_response(vendor: VendorProfile) -> Response:
    return Response(
        {
            'message': 'Your vendor profile is not verified yet.',
            'status': vendor.verification_status,
            'last_submitted_at': vendor.last_submitted_at,
            'can_resubmit': vendor.verification_status in {
                VendorProfile.VerificationStatus.PENDING,
                VendorProfile.VerificationStatus.REJECTED,
            },
            'blocked': vendor.verification_status == VendorProfile.VerificationStatus.BLOCKED,
        },
        status=status.HTTP_403_FORBIDDEN,
    )


class VendorProfileView(generics.RetrieveUpdateAPIView):
    """
    Vendor profile management for authenticated vendors.
    GET returns their own profile, PUT/PATCH allows updates.
    """
    permission_classes = [permissions.IsAuthenticated, IsVendorOwner]
    serializer_class = VendorDetailSerializer
    lookup_field = 'slug'

    def get_object(self):
        # Return the vendor profile of the authenticated user
        try:
            return self.request.user.vendor_profile
        except VendorProfile.DoesNotExist:
            raise NotFound("Vendor profile not found for this user.")


class VendorProfileSubmissionView(generics.UpdateAPIView):
    """Submit or re-submit vendor profile data for admin verification."""
    permission_classes = [permissions.IsAuthenticated, IsVendorOwner]
    serializer_class = VendorProfileSubmissionSerializer

    def get_object(self):
        try:
            return self.request.user.vendor_profile
        except VendorProfile.DoesNotExist:
            raise NotFound('Vendor profile not found for this user.')

    def patch(self, request, *args, **kwargs):
        vendor = self.get_object()

        if vendor.verification_status == VendorProfile.VerificationStatus.BLOCKED:
            return Response(
                {
                    'message': 'Your vendor profile is blocked. You cannot re-submit your information.',
                    'status': vendor.verification_status,
                    'last_submitted_at': vendor.last_submitted_at,
                    'can_resubmit': False,
                    'blocked': True,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        had_previous_submission = bool(vendor.last_submitted_at)
        serializer = self.get_serializer(vendor, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            verification_status=VendorProfile.VerificationStatus.PENDING,
            last_submitted_at=timezone.now(),
        )

        vendor.refresh_from_db()
        return Response(
            {
                'message': (
                    'Vendor profile re-submitted successfully. It is now pending admin review.'
                    if had_previous_submission
                    else 'Vendor profile submitted successfully. It is now pending admin review.'
                ),
                'status': vendor.verification_status,
                'last_submitted_at': vendor.last_submitted_at,
                'can_resubmit': True,
                'blocked': False,
                'vendor_profile': SimpleVendorProfileSerializer(vendor, context={'request': request}).data,
            },
            status=status.HTTP_200_OK,
        )


class StoreListView(generics.ListAPIView):
    """
    List of all active stores. Returns basic info + avg rating.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = SimpleVendorProfileSerializer
    pagination_class = StandardResultsSetPagination
    queryset = VendorProfile.objects.filter(
        is_active=True,
        verification_status=VendorProfile.VerificationStatus.APPROVED,
    ).order_by('-created_at')


class StoreDetailView(generics.RetrieveAPIView):
    """
    Public store page — returns vendor profile + paginated product list.
    Supports ?category=<slug> filter on the product list.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = VendorDetailSerializer
    lookup_field = 'slug'
    queryset = VendorProfile.objects.filter(
        is_active=True,
        verification_status=VendorProfile.VerificationStatus.APPROVED,
    )

    def get_permissions(self):
        if self.kwargs.get('slug') is None:
            return [IsVendorOwner()]
        return super().get_permissions()

    def get_object(self):
        slug = self.kwargs.get('slug')
        try:
            if slug:
                return VendorProfile.objects.get(
                    slug=slug,
                    is_active=True,
                    verification_status=VendorProfile.VerificationStatus.APPROVED,
                )
            else:
                # If no slug provided, return the vendor profile of the authenticated user
                return self.request.user.vendor_profile
        except VendorProfile.DoesNotExist:
            raise NotFound("Vendor not found.")

    def retrieve(self, request, *args, **kwargs):
        vendor = self.get_object()

        # /store/ means "my own vendor store". Keep it gated to approved profiles.
        if self.kwargs.get('slug') is None and vendor.verification_status != VendorProfile.VerificationStatus.APPROVED:
            return _pending_vendor_response(vendor)

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

class VendorCreateProductView(generics.CreateAPIView):
    """
    Endpoint for vendors to create new products.
    """
    permission_classes = [permissions.IsAuthenticated, IsVendorOwner]
    serializer_class = ProductCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = ProductCreateSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(vendor=request.user.vendor_profile)
        return Response(
            {"message": "Product created successfully."},
            status=status.HTTP_201_CREATED
        )

