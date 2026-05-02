import uuid, requests
from django.conf import settings
from django.core.cache import cache
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework import status as drf_status
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError, NotFound
from .services.delivery_charge_service import DeliveryChargeService, DeliveryChargeRequest

from .models import Order, PathaoCity, PathaoZone, PathaoArea
from .serializers import (
    CheckoutSerializer,
    OrderSerializer,
    PathaoCitySerializer,
    PathaoZoneSerializer,
    PathaoAreaSerializer,
)
from .utils.pathao_util import get_access_token, get_cities, get_zones, get_areas
from .services.checkout_service import CheckoutService, CheckoutError
from apps.accounts.models import UserAddress
from apps.cart.models import Cart

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
            .prefetch_related('items', 'payment', 'sub_orders__items')
            .order_by('-created_at')
        )


class OrderDetailView(generics.RetrieveAPIView):
    """Retrieve a single order by id (UUID)."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer
    lookup_field = 'pk'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items', 'payment', 'sub_orders__items')


class CheckoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CheckoutSerializer

    def post(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address_id = serializer.validated_data['address_id']
        payment_type = serializer.validated_data['payment_type']

        try:
            address = UserAddress.objects.select_related('city', 'zone', 'area').get(
                id=address_id, user=request.user
            )
        except UserAddress.DoesNotExist:
            return Response({'detail': 'Address not found.'}, status=status.HTTP_404_NOT_FOUND)

        cart = (
            Cart.objects
            .select_related('voucher')
            .prefetch_related(
                'items__product__vendor',
                'items__variant__options__variant_type',
            )
            .filter(user=request.user)
            .first()
        )

        try:
            service = CheckoutService(
                user=request.user,
                address=address,
                cart=cart,
                payment_type=payment_type,
                request=request,
            )
            order, payment_url = service.execute()
        except CheckoutError as exc:
            return Response({'detail': exc.message}, status=exc.status)

        return Response(
            {
                'message': 'Checkout completed.' if payment_type == 'cod' else 'Checkout initiated.',
                'payment_type': payment_type,
                'payment_url': payment_url,
                'order': OrderSerializer(order, context={'request': request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


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
            "vendor_id": <int>,
            "address_id": <int>,
            "item_type": <int>,       # default 2
            "delivery_type": <int>,   # default 48
            "item_weight": <float>    # kg, default 0.5
        }
    """
    permission_classes = [permissions.IsAuthenticated]
    service = DeliveryChargeService()

    def post(self, request, *args, **kwargs):
        vendor_id = request.data.get('vendor_id')
        address_id = request.data.get('address_id')

        if not vendor_id or not address_id:
            return Response(
                {"error": "'vendor_id' and 'address_id' are required."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        params = DeliveryChargeRequest(
            vendor_id=int(vendor_id),
            address_id=int(address_id),
            item_type=int(request.data.get('item_type', 2)),
            delivery_type=int(request.data.get('delivery_type', 48)),
            item_weight=float(request.data.get('item_weight', 0.5)),
        )

        try:
            result = self.service.calculate(request.user, params)
            return Response(
                {
                    'delivery_charge': result.delivery_charge,
                    'source': result.source,
                    'raw': result.raw,
                },
                status=drf_status.HTTP_200_OK,
            )
        except (ValidationError, NotFound):
            raise  # DRF handles these automatically with correct status codes
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

class SslCommerzPaymentView(generics.GenericAPIView):
    """Test view to initiate a payment via SSLCommerz."""
    # permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        tran_id = str(uuid.uuid4())
        print(settings.SSLCOMMERZ_STORE_ID, settings.SSLCOMMERZ_STORE_PASSWORD)
        print(settings.SSLCOMMERZ_API_URL)

        base_url = request.build_absolute_uri('/')[:-1] + '/api/v1' 

        payload = {
            "store_id": settings.SSLCOMMERZ_STORE_ID,
            "store_passwd": settings.SSLCOMMERZ_STORE_PASSWORD,

            "total_amount": 100,
            "currency": "BDT",
            "tran_id": tran_id,

            "success_url": f"{base_url}/orders/payment/success/",
            "fail_url": f"{base_url}/orders/payment/fail/",
            "cancel_url": f"{base_url}/orders/payment/cancel/",
            "ipn_url": f"{base_url}/orders/payment/ipn/",

            "cus_name": "Test User",
            "cus_email": "test@mail.com",
            "cus_add1": "Dhaka",
            "cus_phone": "01700000000",

            "product_name": "Test Product",
            "product_category": "General",
            "product_profile": "general",
        }

        response = requests.post(settings.SSLCOMMERZ_API_URL, data=payload)
        data = response.json()

        if data.get("status") == "SUCCESS":
            return Response({"url": data["GatewayPageURL"]})

        return Response({"error": data}, status=400)
