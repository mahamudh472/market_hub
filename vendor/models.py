from django.db import models
from accounts.models import User
from autoslug import AutoSlugField
from orders.models import PathaoCity, PathaoZone, PathaoArea


class VendorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile')
    name = models.CharField(max_length=255)
    slug = AutoSlugField(populate_from='name', unique=True, always_update=False)
    description = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='vendor/logos/', blank=True, null=True)
    banner_image = models.ImageField(upload_to='vendor/banners/', blank=True, null=True)

    # Contact Info
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    secondary_phone = models.CharField(max_length=20, blank=True, null=True)
    otp_number = models.CharField(max_length=6, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.ForeignKey(PathaoCity, on_delete=models.SET_NULL, null=True, blank=True, related_name='vendors')
    zone = models.ForeignKey(PathaoZone, on_delete=models.SET_NULL, null=True, blank=True, related_name='vendors')
    area = models.ForeignKey(PathaoArea, on_delete=models.SET_NULL, null=True, blank=True, related_name='vendors')
    country = models.CharField(max_length=100, blank=True, null=True)

    # Status & trust
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Aggregate rating (updated via signal/task)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = 'vendor_profiles'

    def __str__(self):
        return self.name
