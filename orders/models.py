import uuid
from django.db import models


class Order(models.Model):
    """Customer order header"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=30, unique=True, editable=False)

    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='orders')
    # Snapshot of the delivery address at order time
    delivery_address = models.ForeignKey(
        'accounts.UserAddress', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='orders'
    )
    delivery_address_snapshot = models.JSONField(null=True, blank=True)  # frozen copy

    voucher_code = models.CharField(max_length=50, blank=True, null=True)
    voucher_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    note = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            import random
            import string
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            self.order_number = f"ORD-{suffix}"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """A single line inside an order — per vendor item"""
    ITEM_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    vendor = models.ForeignKey('vendor.VendorProfile', on_delete=models.PROTECT, related_name='order_items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='order_items')
    variant = models.ForeignKey(
        'products.ProductVariant', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='order_items'
    )

    # Snapshots at order time (price can change later)
    product_name = models.CharField(max_length=255)
    variant_details = models.JSONField(null=True, blank=True)  # e.g. {"Size": "M", "Color": "Red"}
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default='pending')

    class Meta:
        db_table = 'order_items'

    def __str__(self):
        return f"{self.order.order_number} — {self.product_name} × {self.quantity}"


class Payment(models.Model):
    """Payment record for an order"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    METHOD_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('card', 'Credit/Debit Card'),
        ('mobile_banking', 'Mobile Banking'),
        ('online', 'Online Payment'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    method = models.CharField(max_length=30, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    gateway_response = models.JSONField(null=True, blank=True)  # raw gateway data

    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments'

    def __str__(self):
        return f"Payment({self.order.order_number}, {self.method}, {self.status})"

# Pathao address db
class PathaoCity(models.Model):
    city_id = models.IntegerField(primary_key=True)
    city_name = models.CharField(max_length=255)

    def __str__(self):
        return self.city_name

class PathaoZone(models.Model):
    zone_id = models.IntegerField(primary_key=True)
    zone_name = models.CharField(max_length=255)
    city = models.ForeignKey(PathaoCity, on_delete=models.CASCADE, related_name='zones')

    def __str__(self):
        return f"{self.zone_name} ({self.city.city_name})"

class PathaoArea(models.Model):
    area_id = models.IntegerField(primary_key=True)
    area_name = models.CharField(max_length=255)
    zone = models.ForeignKey(PathaoZone, on_delete=models.CASCADE, related_name='areas')
    home_delivery_available = models.BooleanField(default=False)
    pickup_available = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.area_name} ({self.zone.zone_name}, {self.zone.city.city_name})"
