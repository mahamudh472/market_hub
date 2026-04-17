from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
import uuid
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email must be provided')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)

class Role(models.TextChoices):
    CUSTOMER = 'customer', 'Customer'
    VENDOR = 'vendor', 'Vendor'
    ADMIN = 'admin', 'Admin'

class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model without mandatory username"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=255)
    username = models.CharField(max_length=150, blank=True, null=True)
    full_name = models.CharField(max_length=30, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True,
                              choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    age = models.IntegerField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    
    joined_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # nothing else required for createsuperuser

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email

class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')


class OTP(models.Model):
    """OTP for authentication purposes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'otps'
        verbose_name = 'OTP'
        verbose_name_plural = 'OTPs'
    
    def __str__(self):
        return f"{self.user.email} - {self.code}"
    
    def is_valid(self):
        """Check if OTP is still valid"""
        return not self.is_used and timezone.now() < self.expires_at


class UserAddress(models.Model):
    """Saved delivery addresses for a user"""
    ADDRESS_TYPES = [
        ('home', 'Home'),
        ('office', 'office'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=20, choices=ADDRESS_TYPES, default='home')
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    landmark = models.CharField(max_length=255, blank=True, null=True)
    # Pathao-linked city & zone (used for delivery charge calculation)
    city = models.ForeignKey(
        'orders.PathaoCity',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='user_addresses',
    )
    zone = models.ForeignKey(
        'orders.PathaoZone',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='user_addresses',
    )
    area = models.ForeignKey(
        'orders.PathaoArea',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='user_addresses',
    )
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, default='Bangladesh')
    is_default_delivery = models.BooleanField(default=False)
    is_default_billing = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_addresses'
        ordering = ['-is_default_delivery', '-created_at']

    def __str__(self):
        city_name = self.city.city_name if self.city else 'N/A'
        return f"{self.user.email} — {self.label} ({city_name})"

    def save(self, *args, **kwargs):
        # Only one default address per user
        if self.is_default_delivery:
            UserAddress.objects.filter(user=self.user, is_default_delivery=True).exclude(pk=self.pk).update(is_default_delivery=False)
        super().save(*args, **kwargs)


