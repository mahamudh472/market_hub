from django.db import models


class HomeBanner(models.Model):
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to='home_banners/')
    destination_url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'home_banners'
        ordering = ['sort_order', '-created_at']

    def __str__(self):
        return self.title


class Wishlist(models.Model):
    """Per-user product wishlist"""
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wishlists'
        unique_together = ('user', 'product')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.email} → {self.product.name}"


class DeliveryCharge(models.Model):
    """Simple delivery charge configuration (dummy for now)"""
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True, null=True)
    charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Free delivery above this amount. Leave blank to always charge."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'delivery_charges'

    def __str__(self):
        return f"{self.name} — {self.charge}"
