from dataclasses import dataclass
from typing import Optional

from rest_framework.exceptions import ValidationError, NotFound

from apps.vendor.models import VendorProfile
from apps.accounts.models import UserAddress
from apps.orders.utils.delivery_charge import calculate_delivery_charge_for_vendor  # adjust import path



@dataclass
class DeliveryChargeRequest:
    vendor_id: int
    address_id: int
    item_type: int = 2
    delivery_type: int = 48
    item_weight: float = 0.5


@dataclass
class DeliveryChargeResult:
    delivery_charge: str
    source: str
    raw: dict


class DeliveryChargeService:

    def calculate(self, user, params: DeliveryChargeRequest) -> DeliveryChargeResult:
        vendor = self._get_vendor(params.vendor_id)
        address = self._get_address(params.address_id, user)

        result = calculate_delivery_charge_for_vendor(
            vendor=vendor,
            address=address,
            item_weight=params.item_weight,
            item_type=params.item_type,
            delivery_type=params.delivery_type,
        )

        return DeliveryChargeResult(
            delivery_charge=str(result['amount']),
            source=result['source'],
            raw=result['raw'],
        )

    def _get_vendor(self, vendor_id: int) -> VendorProfile:
        try:
            vendor = VendorProfile.objects.get(pk=vendor_id)
        except VendorProfile.DoesNotExist:
            raise NotFound(f"Vendor with id={vendor_id} not found.")

        if not vendor.pathao_store_id:
            raise ValidationError("This vendor does not have a Pathao store configured yet.")

        return vendor

    def _get_address(self, address_id: int, user) -> UserAddress:
        try:
            address = UserAddress.objects.select_related('city', 'zone').get(
                pk=address_id, user=user
            )
        except UserAddress.DoesNotExist:
            raise NotFound(f"Address with id={address_id} not found for this user.")

        if not address.city or not address.zone:
            raise ValidationError("The selected address does not have a Pathao city and zone set.")

        return address
