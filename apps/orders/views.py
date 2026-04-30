from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status as drf_status
from rest_framework.views import APIView

from .models import Order, OrderItem, Payment, SiteSettings, SubOrder, PathaoCity, PathaoZone, PathaoArea
from .serializers import (
    CheckoutSerializer,
    OrderSerializer,
    PathaoCitySerializer,
    PathaoZoneSerializer,
    PathaoAreaSerializer,
)
from .utils.pathao_util import get_access_token, get_cities, get_zones, get_areas
from .utils.delivery_charge import calculate_delivery_charge_for_vendor
from .utils.ssl_commerz_util import initiate_sslcommerz_payment


MONEY_QUANT = Decimal('0.01')


def _quantize_money(value):
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _address_snapshot(address):
    return {
        'id': address.id,
        'label': address.label,
        'full_name': address.full_name,
        'phone_number': address.phone_number,
        'address': address.address,
        'landmark': address.landmark,
        'postal_code': address.postal_code,
        'country': address.country,
        'city_id': address.city_id,
        'city_name': address.city.city_name if address.city else None,
        'zone_id': address.zone_id,
        'zone_name': address.zone.zone_name if address.zone else None,
        'area_id': address.area_id,
        'area_name': address.area.area_name if address.area else None,
    }


def _variant_snapshot(variant):
    if not variant:
        return None
    return {
        'id': str(variant.id),
        'options': {
            option.variant_type.name: option.value
            for option in variant.options.select_related('variant_type').all()
        },
    }


def _calculate_tax(amount_after_discount, tax_percent):
    if amount_after_discount <= Decimal('0'):
        return Decimal('0.00')
    return _quantize_money(amount_after_discount * (tax_percent / Decimal('100')))


def _build_discount_allocation(vendor_rows, total_discount, total_subtotal):
    if total_discount <= Decimal('0') or total_subtotal <= Decimal('0'):
        return {row['vendor'].id: Decimal('0.00') for row in vendor_rows}

    allocations = {}
    allocated_total = Decimal('0.00')
    for row in vendor_rows:
        ratio = row['subtotal'] / total_subtotal
        discount = _quantize_money(total_discount * ratio)
        allocations[row['vendor'].id] = discount
        allocated_total += discount

    remainder = _quantize_money(total_discount - allocated_total)
    if remainder != Decimal('0.00') and vendor_rows:
        last_vendor_id = vendor_rows[-1]['vendor'].id
        allocations[last_vendor_id] = _quantize_money(allocations[last_vendor_id] + remainder)
    return allocations


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
    """
    Checkout endpoint.
    - Receives address_id and payment_type (cod/paynow)
    - Groups cart items by vendor
    - Creates parent order + per-vendor sub-orders + order items
    - Creates payment and returns SSLCommerz link for paynow
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CheckoutSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        from accounts.models import UserAddress
        from cart.models import Cart, VoucherUsage

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address_id = serializer.validated_data['address_id']
        payment_type = serializer.validated_data['payment_type']

        try:
            address = UserAddress.objects.select_related('city', 'zone', 'area').get(
                id=address_id,
                user=request.user,
            )
        except UserAddress.DoesNotExist:
            return Response({'detail': 'Address not found.'}, status=drf_status.HTTP_404_NOT_FOUND)

        if not address.city_id or not address.zone_id:
            return Response(
                {'detail': 'Selected address must have Pathao city and zone.'},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

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

        if not cart or not cart.items.exists():
            return Response({'detail': 'Cart is empty.'}, status=drf_status.HTTP_400_BAD_REQUEST)

        site_settings = SiteSettings.get_solo()
        if payment_type == 'cod' and not site_settings.is_cod_enabled:
            return Response({'detail': 'COD is currently disabled.'}, status=drf_status.HTTP_400_BAD_REQUEST)

        cart_items = list(cart.items.select_related('product__vendor', 'variant').all())
        for item in cart_items:
            stock = item.variant.stock if item.variant else item.product.stock
            if item.quantity > stock:
                return Response(
                    {'detail': f'Insufficient stock for {item.product.name}. Available: {stock}.'},
                    status=drf_status.HTTP_400_BAD_REQUEST,
                )

        subtotal = _quantize_money(sum((item.total_price for item in cart_items), Decimal('0')))
        total_discount = _quantize_money(cart.get_discount())

        vendor_grouped = defaultdict(list)
        for item in cart_items:
            vendor_grouped[item.product.vendor_id].append(item)

        vendor_rows = []
        for items in vendor_grouped.values():
            vendor = items[0].product.vendor
            vendor_subtotal = _quantize_money(sum((line.total_price for line in items), Decimal('0')))
            total_qty = sum(line.quantity for line in items)
            total_weight = max(0.5, float(total_qty) * 0.2)
            delivery_result = calculate_delivery_charge_for_vendor(
                vendor=vendor,
                address=address,
                item_weight=total_weight,
            )

            free_delivery_threshold = Decimal(str(site_settings.free_delivery_min_order))
            if free_delivery_threshold > Decimal('0') and subtotal >= free_delivery_threshold:
                delivery_charge = Decimal('0.00')
            else:
                delivery_charge = _quantize_money(delivery_result['amount'])

            vendor_rows.append(
                {
                    'vendor': vendor,
                    'items': items,
                    'subtotal': vendor_subtotal,
                    'delivery_charge': delivery_charge,
                    'delivery_meta': delivery_result,
                }
            )

        discount_by_vendor = _build_discount_allocation(vendor_rows, total_discount, subtotal)
        tax_percent = Decimal(str(site_settings.tax_percent))
        platform_fee = _quantize_money(site_settings.platform_fee)
        cod_charge = _quantize_money(site_settings.cod_fee if payment_type == 'cod' else 0)

        parent_tax = Decimal('0.00')
        parent_delivery_charge = Decimal('0.00')
        parent_platform_fee = Decimal('0.00')
        parent_total = Decimal('0.00')

        order = Order.objects.create(
            user=request.user,
            delivery_address=address,
            delivery_address_snapshot=_address_snapshot(address),
            voucher_code=cart.voucher.code if cart.voucher else None,
            voucher_discount=total_discount,
            subtotal=subtotal,
            tax=Decimal('0.00'),
            delivery_charge=Decimal('0.00'),
            platform_fee=Decimal('0.00'),
            cod_charge=cod_charge,
            total=Decimal('0.00'),
            status='confirmed' if payment_type == 'cod' else 'pending',
        )

        for row in vendor_rows:
            vendor = row['vendor']
            vendor_discount = discount_by_vendor.get(vendor.id, Decimal('0.00'))
            taxable_amount = _quantize_money(row['subtotal'] - vendor_discount)
            if taxable_amount < Decimal('0.00'):
                taxable_amount = Decimal('0.00')

            vendor_tax = _calculate_tax(taxable_amount, tax_percent)
            vendor_total = _quantize_money(
                taxable_amount + vendor_tax + row['delivery_charge'] + platform_fee
            )

            sub_order = SubOrder.objects.create(
                parent_order=order,
                vendor=vendor,
                subtotal=row['subtotal'],
                voucher_discount=vendor_discount,
                tax=vendor_tax,
                delivery_charge=row['delivery_charge'],
                platform_fee=platform_fee,
                total=vendor_total,
                status='confirmed' if payment_type == 'cod' else 'pending',
                note=(
                    f"delivery_source={row['delivery_meta']['source']}; "
                    f"delivery_raw={row['delivery_meta']['raw']}"
                ),
            )
            for cart_item in row['items']:
                OrderItem.objects.create(
                    order=order,
                    sub_order=sub_order,
                    vendor=vendor,
                    product=cart_item.product,
                    variant=cart_item.variant,
                    product_name=cart_item.product.name,
                    variant_details=_variant_snapshot(cart_item.variant),
                    unit_price=_quantize_money(cart_item.unit_price),
                    quantity=cart_item.quantity,
                    total_price=_quantize_money(cart_item.total_price),
                    status='confirmed' if payment_type == 'cod' else 'pending',
                )

                if cart_item.variant:
                    cart_item.variant.stock = max(0, cart_item.variant.stock - cart_item.quantity)
                    cart_item.variant.save(update_fields=['stock'])
                else:
                    cart_item.product.stock = max(0, cart_item.product.stock - cart_item.quantity)
                    cart_item.product.save(update_fields=['stock'])

            parent_tax += vendor_tax
            parent_delivery_charge += row['delivery_charge']
            parent_platform_fee += platform_fee
            parent_total += vendor_total

        parent_total = _quantize_money(parent_total + cod_charge)
        order.tax = _quantize_money(parent_tax)
        order.delivery_charge = _quantize_money(parent_delivery_charge)
        order.platform_fee = _quantize_money(parent_platform_fee)
        order.total = parent_total
        order.save(update_fields=['tax', 'delivery_charge', 'platform_fee', 'cod_charge', 'total', 'updated_at'])

        payment_method = 'cod' if payment_type == 'cod' else 'online'
        payment = Payment.objects.create(
            order=order,
            method=payment_method,
            status='pending',
            amount=order.total,
        )

        payment_url = None
        if payment_type == 'paynow':
            try:
                payment_session = initiate_sslcommerz_payment(
                    request=request,
                    order=order,
                    address_snapshot=order.delivery_address_snapshot or {},
                )
                payment_url = payment_session['payment_url']
                payment.transaction_id = payment_session['transaction_id']
                payment.gateway_response = payment_session['gateway_response']
                payment.save(update_fields=['transaction_id', 'gateway_response'])
            except Exception as exc:
                transaction.set_rollback(True)
                return Response(
                    {'detail': f'Could not create payment session: {exc}'},
                    status=drf_status.HTTP_400_BAD_REQUEST,
                )

        if cart.voucher:
            voucher = cart.voucher
            VoucherUsage.objects.create(voucher=voucher, user=request.user)
            voucher.used_count += 1
            voucher.save(update_fields=['used_count'])

        cart.items.all().delete()
        cart.voucher = None
        cart.save(update_fields=['voucher', 'updated_at'])

        order_data = OrderSerializer(order, context={'request': request}).data
        return Response(
            {
                'message': 'Checkout completed.' if payment_type == 'cod' else 'Checkout initiated.',
                'payment_type': payment_type,
                'payment_url': payment_url,
                'order': order_data,
            },
            status=drf_status.HTTP_201_CREATED,
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
            "vendor_id": <int>,          # VendorProfile pk
            "address_id": <int>,         # UserAddress pk
            "item_type": <int>,          # Pathao item type (default 2)
            "delivery_type": <int>,      # Pathao delivery type (default 48)
            "item_weight": <float>       # weight in kg (default 0.5)
        }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
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

        try:
            result = calculate_delivery_charge_for_vendor(
                vendor=vendor,
                address=address,
                item_weight=item_weight,
                item_type=item_type,
                delivery_type=delivery_type,
            )
            return Response(
                {
                    'delivery_charge': str(result['amount']),
                    'source': result['source'],
                    'raw': result['raw'],
                },
                status=drf_status.HTTP_200_OK,
            )

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

import uuid, requests
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
