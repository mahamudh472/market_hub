from django.db import models
from apps.accounts.models import User
from autoslug import AutoSlugField
from apps.orders.models import PathaoCity, PathaoZone, PathaoArea


class VendorProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        BLOCKED = 'blocked', 'Blocked'

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
    otp_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.ForeignKey(PathaoCity, on_delete=models.SET_NULL, null=True, blank=True, related_name='vendors')
    zone = models.ForeignKey(PathaoZone, on_delete=models.SET_NULL, null=True, blank=True, related_name='vendors')
    area = models.ForeignKey(PathaoArea, on_delete=models.SET_NULL, null=True, blank=True, related_name='vendors')
    country = models.CharField(max_length=100, blank=True, null=True)

    pathao_store_id = models.CharField(max_length=255, blank=True, null=True)  # Store ID from Pathao API
    pathao_store_status = models.CharField(max_length=50, blank=True, null=True)  # e.g., 'active', 'inactive', 'pending'
    pathao_store_name = models.CharField(max_length=255, blank=True, null=True)  # Store name as registered in Pathao

    # Status & trust
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    last_submitted_at = models.DateTimeField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    recommended = models.BooleanField(default=False)  

    profile_completed = models.BooleanField(default=False)  # Set to True when all required fields are filled

    # Aggregate rating (updated via signal/task)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = 'vendor_profiles'

    def save(self, *args, **kwargs):
        # Keep the legacy boolean flag aligned with the source-of-truth status.
        self.is_verified = self.verification_status == self.VerificationStatus.APPROVED
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
