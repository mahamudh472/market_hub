from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.accounts.models import User, CustomerProfile
from apps.vendor.models import VendorProfile


def _default_vendor_name(instance: User) -> str:
    if instance.full_name:
        return instance.full_name
    return instance.email.split('@')[0]

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.role == 'customer':
            CustomerProfile.objects.create(user=instance)
        elif instance.role == 'vendor':
            VendorProfile.objects.create(
                user=instance,
                name=_default_vendor_name(instance),
                verification_status=VendorProfile.VerificationStatus.PENDING,
            )

