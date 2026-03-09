import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Voucher(models.Model):
    """Discount vouchers / promo codes"""
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    # percentage cap
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Usage limits
    usage_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Null = unlimited")
    per_user_limit = models.PositiveIntegerField(default=1)
    used_count = models.PositiveIntegerField(default=0)

    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    # Vendor-specific vouchers (null = site-wide)
    vendor = models.ForeignKey(
        'vendor.VendorProfile', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='vouchers',
        help_text="Leave blank for site-wide vouchers."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vouchers'

    def __str__(self):
        return self.code

    def calculate_discount(self, cart_total):
        """Return the actual discount amount for the given cart total."""
        from decimal import Decimal
        total = Decimal(str(cart_total))
        if total < self.min_order_amount:
            return Decimal('0')
        if self.discount_type == 'percentage':
            discount = total * (self.discount_value / 100)
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = min(self.discount_value, total)
        return discount


class VoucherUsage(models.Model):
    """Track per-user voucher usage"""
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='voucher_usages')
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'voucher_usages'

    def __str__(self):
        return f"{self.user.email} used {self.voucher.code}"


class Cart(models.Model):
    """One active cart per user"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='cart')
    voucher = models.ForeignKey(
        Voucher, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='carts'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'carts'

    def __str__(self):
        return f"Cart({self.user.email})"

    TAX_RATE = 0.05  # 5 % VAT

    def get_subtotal(self):
        from decimal import Decimal
        total = Decimal('0')
        for item in self.items.select_related('product', 'variant').all():
            unit_price = item.variant.discounted_price if item.variant else item.product.discounted_price
            total += Decimal(str(unit_price)) * item.quantity
        return total

    def get_discount(self):
        from decimal import Decimal
        if not self.voucher:
            return Decimal('0')
        return self.voucher.calculate_discount(self.get_subtotal())

    def get_tax(self):
        from decimal import Decimal
        taxable = self.get_subtotal() - self.get_discount()
        if taxable < Decimal('0'):
            taxable = Decimal('0')
        return (taxable * Decimal(str(self.TAX_RATE))).quantize(Decimal('0.01'))

    def get_total(self, delivery_charge=None):
        from decimal import Decimal
        delivery = Decimal(str(delivery_charge)) if delivery_charge else Decimal('0')
        return self.get_subtotal() - self.get_discount() + self.get_tax() + delivery


class CartItem(models.Model):
    """Line item inside a cart"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='cart_items')
    variant = models.ForeignKey(
        'products.ProductVariant', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cart_items'
        unique_together = ('cart', 'product', 'variant')

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"

    @property
    def unit_price(self):
        if self.variant:
            return self.variant.discounted_price
        return self.product.discounted_price

    @property
    def total_price(self):
        from decimal import Decimal
        return Decimal(str(self.unit_price)) * self.quantity
