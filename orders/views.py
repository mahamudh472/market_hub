from django.conf import settings
from django.core.cache import cache
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status as drf_status
from rest_framework.views import APIView

from .models import Order, PathaoCity, PathaoZone, PathaoArea
from .serializers import (
    OrderSerializer,
    PathaoCitySerializer,
    PathaoZoneSerializer,
    PathaoAreaSerializer,
)
from .utils.pathao_util import get_access_token, get_cities, get_zones, get_areas


PATHAO_LOCATION_CACHE_TIMEOUT = getattr(settings, 'PATHAO_LOCATION_CACHE_TIMEOUT', 60 * 60 * 24)


def _cached_list_response(cache_key, builder):
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data

    data = builder()
    cache.set(cache_key, data, PATHAO_LOCATION_CACHE_TIMEOUT)
    return data


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
            zones_inside_first_city = []
            zones_inside_first_city = get_zones(access_token, cities[0]['city_id']) if cities else []
            areas_inside_first_zone = get_areas(access_token, zones_inside_first_city[0]['zone_id']) if zones_inside_first_city else []
            return Response({"cities": cities, "zones": zones_inside_first_city, "areas": areas_inside_first_zone})
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class GetStoresView(generics.GenericAPIView):
    """Test view to get stores from Pathao API."""
    # permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            from .utils.pathao_util import get_stores
            access_token = get_access_token()
            stores = get_stores(access_token)
            return Response({"stores": stores})
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class CreateStoreView(generics.GenericAPIView):
    """Test view to create a store in Pathao API."""
    # permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            from .utils.pathao_util import create_store
            access_token = get_access_token()
            store_data = {
                "name": "Demo Store 12345",
                "contact_name": "Test Merchant",
                "contact_number": "01700000000",
                # "contact_email": "info.vendor@gmail.com",
                "secondary_contact": "01500000000",
                "otp_number": "01700000000",
                "address": "House 123, Road 4, Sector 10, Uttara, Dhaka-1230, Bangladesh",
                "city_id": 1,  # Example city_id
                "zone_id": 1,  # Example zone_id
                "area_id": 1   # Example area_id
            }
            response = create_store(access_token, **store_data)
            return Response({"store_creation_response": response})
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class CalculateDeliveryChargeView(generics.GenericAPIView):
    """
    Calculate the Pathao delivery charge for a given vendor store and
    a user's saved address.

    POST body:
        {
            "vendor_id": <int>,          # VendorProfile pk
            "address_id": <int>,         # UserAddress pk
            "item_type": <int>,          # Pathao item type (default 2)
            "delivery_type": <int>,      # Pathao delivery type (default 48)
            "item_weight": <float>       # weight in kg (default 0.5)
        }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        from .utils.pathao_util import get_price_plan
        from vendor.models import VendorProfile
        from accounts.models import UserAddress

        vendor_id = request.data.get('vendor_id')
        address_id = request.data.get('address_id')
        item_type = int(request.data.get('item_type', 2))
        delivery_type = int(request.data.get('delivery_type', 48))
        item_weight = float(request.data.get('item_weight', 0.5))

        if not vendor_id or not address_id:
            return Response(
                {"error": "'vendor_id' and 'address_id' are required."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        # --- Fetch vendor and its Pathao store id ---
        try:
            vendor = VendorProfile.objects.get(pk=vendor_id)
        except VendorProfile.DoesNotExist:
            return Response(
                {"error": f"Vendor with id={vendor_id} not found."},
                status=drf_status.HTTP_404_NOT_FOUND,
            )

        if not vendor.pathao_store_id:
            return Response(
                {"error": "This vendor does not have a Pathao store configured yet."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        # --- Fetch user address and extract city / zone ---
        try:
            address = UserAddress.objects.select_related('city', 'zone').get(
                pk=address_id, user=request.user
            )
        except UserAddress.DoesNotExist:
            return Response(
                {"error": f"Address with id={address_id} not found for this user."},
                status=drf_status.HTTP_404_NOT_FOUND,
            )

        if not address.city or not address.zone:
            return Response(
                {"error": "The selected address does not have a Pathao city and zone set."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        recipient_city = address.city.city_id
        recipient_zone = address.zone.zone_id

        try:
            access_token = get_access_token()
            price_data = get_price_plan(
                access_token=access_token,
                store_id=int(vendor.pathao_store_id),
                item_type=item_type,
                delivery_type=delivery_type,
                item_weight=item_weight,
                recipient_city=recipient_city,
                recipient_zone=recipient_zone,
            )
            return Response({"delivery_charge": price_data}, status=drf_status.HTTP_200_OK)

        except Exception as exc:
            return Response({"error": str(exc)}, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)


class PathaoCityListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        cache_key = 'pathao:cities:v1'

        def build_data():
            queryset = PathaoCity.objects.all().order_by('city_name')
            return PathaoCitySerializer(queryset, many=True).data

        data = _cached_list_response(cache_key, build_data)
        return Response({'count': len(data), 'results': data}, status=drf_status.HTTP_200_OK)


class PathaoZoneListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        city_id = request.query_params.get('city_id')
        if not city_id:
            return Response(
                {'detail': 'city_id query parameter is required.'},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        try:
            city_id = int(city_id)
        except (TypeError, ValueError):
            return Response(
                {'detail': 'city_id must be a valid integer.'},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        cache_key = f'pathao:zones:v1:{city_id}'

        def build_data():
            queryset = PathaoZone.objects.filter(city_id=city_id).order_by('zone_name')
            return PathaoZoneSerializer(queryset, many=True).data

        data = _cached_list_response(cache_key, build_data)
        return Response({'city_id': city_id, 'count': len(data), 'results': data}, status=drf_status.HTTP_200_OK)


class PathaoAreaListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        zone_id = request.query_params.get('zone_id')
        if not zone_id:
            return Response(
                {'detail': 'zone_id query parameter is required.'},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        try:
            zone_id = int(zone_id)
        except (TypeError, ValueError):
            return Response(
                {'detail': 'zone_id must be a valid integer.'},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        cache_key = f'pathao:areas:v1:{zone_id}'

        def build_data():
            queryset = PathaoArea.objects.filter(zone_id=zone_id).order_by('area_name')
            return PathaoAreaSerializer(queryset, many=True).data

        data = _cached_list_response(cache_key, build_data)
        return Response({'zone_id': zone_id, 'count': len(data), 'results': data}, status=drf_status.HTTP_200_OK)
