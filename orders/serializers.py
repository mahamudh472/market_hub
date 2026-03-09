from rest_framework import serializers
from .models import Order, OrderItem, Payment


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

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status',
            'subtotal', 'voucher_code', 'voucher_discount',
            'tax', 'delivery_charge', 'total',
            'delivery_address_snapshot',
            'note',
            'items', 'payment',
            'created_at', 'updated_at',
        ]
