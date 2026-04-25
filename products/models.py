from django.db import models
from autoslug import AutoSlugField
from vendor.models import VendorProfile
import uuid

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = AutoSlugField(populate_from="name", unique=True, always_update=False)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    image = models.ImageField(upload_to='category_images/', null=True, blank=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')

    product_details = models.TextField(null=True, blank=True)
    return_policy = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def discounted_price(self):
        if self.discount:
            discount_amount = (1 - self.discount / 100) * self.price
            return discount_amount
        return self.price

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')
    thumbnail = models.BooleanField(default=False)

class ProductVariantType(models.Model):
    """Represents a variant dimension, e.g. 'Size', 'Color'"""
    product = models.ForeignKey(
        'Product', on_delete=models.CASCADE, related_name='variant_types'
    )
    name = models.CharField(max_length=100)  # e.g. "Size", "Color"

    def __str__(self):
        return f"{self.product.name} — {self.name}"


class ProductVariantOption(models.Model):
    """Represents a single option value, e.g. 'SM', 'M', 'XL'"""
    variant_type = models.ForeignKey(
        ProductVariantType, on_delete=models.CASCADE, related_name='options'
    )
    value = models.CharField(max_length=100)  # e.g. "SM", "Red"

    def __str__(self):
        return f"{self.variant_type.name}: {self.value}"


class ProductVariant(models.Model):
    """
    A specific combination of options with its own price/stock/image.
    e.g. Size=SM + Color=Red → price=$10, stock=5
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        'Product', on_delete=models.CASCADE, related_name='variants'
    )
    options = models.ManyToManyField(
        ProductVariantOption, related_name='variants'
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True
    )
    stock = models.PositiveIntegerField()
    image = models.ImageField(
        upload_to='variant_images/', null=True, blank=True
    )

    def __str__(self):
        opts = ", ".join(
            f"{o.variant_type.name}={o.value}" for o in self.options.all()
        )
        return f"{self.product.name} [{opts}]"

    @property
    def discounted_price(self):
        if self.discount:
            return (1 - self.discount / 100) * self.price
        return self.price

class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    rating = models.PositiveIntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class ProductReviewImage(models.Model):
    review = models.ForeignKey(ProductReview, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='review_images/')

