from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import User, CustomerProfile
from vendor.models import VendorProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.role == 'customer':
            CustomerProfile.objects.create(user=instance)
        elif instance.role == 'vendor':
            VendorProfile.objects.create(user=instance)

