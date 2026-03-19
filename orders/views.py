from rest_framework import generics, permissions
from rest_framework.response import Response

from .models import Order
from .serializers import OrderSerializer
from .utils.pathao_util import get_access_token, get_cities


class OrderListView(generics.ListAPIView):
    """List the authenticated user's orders."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return (
            Order.objects
            .filter(user=self.request.user)
            .prefetch_related('items', 'payment')
            .order_by('-created_at')
        )


class OrderDetailView(generics.RetrieveAPIView):
    """Retrieve a single order by id (UUID)."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer
    lookup_field = 'pk'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items', 'payment')


class Test_pathao(generics.GenericAPIView):
    """Test view to check Pathao API integration."""
    # permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            access_token = get_access_token()
            cities = get_cities(access_token)
            return Response({"cities": cities})
        except Exception as e:
            return Response({"error": str(e)}, status=500)
