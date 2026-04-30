import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import VendorProfile

logger = logging.getLogger(__name__)

# Fields required for a Pathao store to be created
REQUIRED_STORE_FIELDS = [
    'name',
    'contact_phone',
    'secondary_phone',
    'otp_number',
    'address',
    'city_id',   # FK to PathaoCity
    'zone_id',   # FK to PathaoZone
    'area_id',   # FK to PathaoArea
]

def _has_required_fields(instance: VendorProfile) -> bool:
    """Return True only when every required field has a non-empty value."""
    for field in REQUIRED_STORE_FIELDS:
        value = getattr(instance, field, None)
        if not value:
            print(f"Missing required field '{field}' for vendor '{instance.name}' (id={instance.pk})")  # Debug log
            return False
    return True


@receiver(post_save, sender=VendorProfile)
def create_pathao_store_on_profile_complete(sender, instance: VendorProfile, created, **kwargs):
    """
    When a VendorProfile is saved and all required fields are populated,
    create a Pathao store (if one hasn't been created yet) and mark the
    profile as completed.
    """
    # Avoid infinite recursion – skip if profile_completed is already True
    # and a store id is already stored.
    if instance.profile_completed and instance.pathao_store_id:
        return

    # Submission is reviewed by admin first; only approved profiles can provision a store.
    if instance.verification_status != VendorProfile.VerificationStatus.APPROVED:
        return

    # Only proceed if all required fields are filled in
    if not _has_required_fields(instance):
        return

    try:
        from apps.orders.utils.pathao_util import get_access_token, create_store

        access_token = get_access_token()

        store_data = create_store(
            access_token=access_token,
            name=instance.name,
            contact_name=instance.name,          # store name used as contact name
            contact_number=instance.contact_phone,
            secondary_contact=instance.secondary_phone,
            otp_number=instance.otp_number,
            address=instance.address,
            city_id=instance.city_id,
            zone_id=instance.zone_id,
            area_id=instance.area_id,
        )

        # store_data == {"store_id": 150140, "store_name": "Demo Store 12345"}
        store_id = store_data.get('store_id')
        store_name = store_data.get('store_name')

        # Save without triggering this signal again by using update()
        VendorProfile.objects.filter(pk=instance.pk).update(
            pathao_store_id=str(store_id),
            pathao_store_name=store_name,
            pathao_store_status='active',
            profile_completed=True,
        )

        logger.info(
            "Pathao store created for vendor '%s': store_id=%s, store_name='%s'",
            instance.name, store_id, store_name,
        )

    except Exception as exc:
        logger.error(
            "Failed to create Pathao store for vendor '%s': %s",
            instance.name, exc,
        )
