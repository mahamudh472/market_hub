from rest_framework import serializers
from .models import Cart, CartItem, Voucher
from apps.products.serializers import SimpleProductSerializer, ProductVariantSerializer


class CartItemSerializer(serializers.ModelSerializer):
    product_detail = SimpleProductSerializer(source='product', read_only=True)
    variant_detail = ProductVariantSerializer(source='variant', read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'variant',
            'product_detail', 'variant_detail',
            'quantity', 'unit_price', 'total_price',
            'added_at',
        ]
        extra_kwargs = {
            'product': {'write_only': True},
            'variant': {'write_only': True, 'required': False},
        }

    def validate(self, attrs):
        product = attrs.get('product')
        variant = attrs.get('variant')
        quantity = attrs.get('quantity', 1)

        if variant:
            if variant.product != product:
                raise serializers.ValidationError("Variant does not belong to this product.")
            if quantity > variant.stock:
                raise serializers.ValidationError(
                    f"Only {variant.stock} units available for this variant."
                )
        else:
            if quantity > product.stock:
                raise serializers.ValidationError(
                    f"Only {product.stock} units available."
                )
        return attrs


class VoucherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voucher
        fields = ['id', 'code', 'discount_type', 'discount_value', 'min_order_amount']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    voucher_detail = VoucherSerializer(source='voucher', read_only=True)
    subtotal = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()
    tax = serializers.SerializerMethodField()
    delivery_charge = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            'id', 'items', 'items_count',
            'voucher_detail',
            'subtotal', 'discount', 'tax', 'delivery_charge', 'total',
        ]

    def _get_delivery(self):
        """Return dummy delivery charge (to be replaced with real logic later)."""
        return 60  # BDT 60 flat rate

    def get_subtotal(self, obj):
        return str(obj.get_subtotal())

    def get_discount(self, obj):
        return str(obj.get_discount())

    def get_tax(self, obj):
        return str(obj.get_tax())

    def get_delivery_charge(self, obj):
        subtotal = obj.get_subtotal()
        # Free delivery above 500
        return 0 if subtotal >= 500 else self._get_delivery()

    def get_total(self, obj):
        delivery = self.get_delivery_charge(obj)
        return str(obj.get_total(delivery_charge=delivery))

    def get_items_count(self, obj):
        return obj.items.count()


class ApplyVoucherSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
