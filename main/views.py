from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .utils.home import get_home_data
from .models import Wishlist
from .serializers import WishlistSerializer
from products.models import Product


class HomeAPIView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        data = get_home_data(user=request.user if request.user.is_authenticated else None, request=request)
        return Response({"data": data}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────
# Wishlist
# ─────────────────────────────────────────
class WishlistListView(generics.ListAPIView):
    """GET /wishlist/ — list user's saved products."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WishlistSerializer

    def get_queryset(self):
        return (
            Wishlist.objects
            .filter(user=self.request.user)
            .select_related('product__vendor', 'product__category')
            .prefetch_related('product__images', 'product__reviews')
        )


class WishlistToggleView(APIView):
    """
    POST /wishlist/<product_id>/toggle/
    Add the product if not present; remove if already in list.
    Returns {added: true/false}.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, product_id):
        product = generics.get_object_or_404(Product, pk=product_id)
        item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
        if not created:
            item.delete()
            return Response({'added': False, 'message': 'Removed from wishlist.'})
        return Response({'added': True, 'message': 'Added to wishlist.'}, status=status.HTTP_201_CREATED)


class WishlistRemoveView(APIView):
    """DELETE /wishlist/<product_id>/  — explicit remove."""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, product_id):
        deleted, _ = Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
        if deleted:
            return Response({'message': 'Removed from wishlist.'})
        return Response({'error': 'Product not in your wishlist.'}, status=status.HTTP_404_NOT_FOUND)
