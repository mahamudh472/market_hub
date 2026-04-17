from rest_framework import serializers
from .models import Order, OrderItem, Payment, SubOrder, PathaoCity, PathaoZone, PathaoArea


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'method', 'status', 'amount', 'transaction_id', 'paid_at', 'created_at']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'variant',
            'product_name', 'variant_details',
            'unit_price', 'quantity', 'total_price',
            'status',
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    payment = PaymentSerializer(read_only=True)
    sub_orders = serializers.SerializerMethodField()

    def get_sub_orders(self, obj):
        queryset = obj.sub_orders.prefetch_related('items').all().order_by('created_at')
        return SubOrderSerializer(queryset, many=True).data

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status',
            'subtotal', 'voucher_code', 'voucher_discount',
            'tax', 'delivery_charge', 'platform_fee', 'cod_charge', 'total',
            'delivery_address_snapshot',
            'note',
            'sub_orders',
            'items', 'payment',
            'created_at', 'updated_at',
        ]


class SubOrderSerializer(serializers.ModelSerializer):
    vendor_id = serializers.IntegerField(source='vendor.id', read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = SubOrder
        fields = [
            'id',
            'vendor_id', 'vendor_name',
            'status',
            'subtotal', 'voucher_discount', 'tax', 'delivery_charge', 'platform_fee', 'total',
            'items',
            'created_at', 'updated_at',
        ]

class SimpleOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'status', 'total', 'created_at']


class PathaoCitySerializer(serializers.ModelSerializer):
    class Meta:
        model = PathaoCity
        fields = ['city_id', 'city_name']


class PathaoZoneSerializer(serializers.ModelSerializer):
    city_id = serializers.IntegerField(source='city.city_id', read_only=True)

    class Meta:
        model = PathaoZone
        fields = ['zone_id', 'zone_name', 'city_id']


class PathaoAreaSerializer(serializers.ModelSerializer):
    zone_id = serializers.IntegerField(source='zone.zone_id', read_only=True)

    class Meta:
        model = PathaoArea
        fields = ['area_id', 'area_name', 'zone_id', 'home_delivery_available', 'pickup_available']


class CheckoutSerializer(serializers.Serializer):
    PAYMENT_TYPE_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('paynow', 'Pay Now'),
    ]

    address_id = serializers.IntegerField()
    payment_type = serializers.ChoiceField(choices=PAYMENT_TYPE_CHOICES)
