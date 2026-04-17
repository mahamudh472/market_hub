from decimal import Decimal

from orders.models import SiteSettings
from orders.utils.pathao_util import get_access_token, get_price_plan


def extract_delivery_amount(price_data):
    """Extract a numeric delivery fee from Pathao's price plan payload."""
    if isinstance(price_data, (int, float, str, Decimal)):
        return Decimal(str(price_data))

    if not isinstance(price_data, dict):
        raise ValueError('Unexpected delivery charge payload from Pathao.')

    candidate_keys = [
        'delivery_fee',
        'delivery_charge',
        'final_price',
        'price',
        'amount',
    ]
    for key in candidate_keys:
        if key in price_data and price_data[key] is not None:
            return Decimal(str(price_data[key]))

    data = price_data.get('data')
    if isinstance(data, dict):
        for key in candidate_keys:
            if key in data and data[key] is not None:
                return Decimal(str(data[key]))

    raise ValueError('Could not determine delivery amount from Pathao price plan response.')


def calculate_delivery_charge_for_vendor(
    vendor,
    address,
    item_weight=0.5,
    item_type=2,
    delivery_type=48,
):
    """
    Calculate Pathao delivery fee for a vendor to the selected customer address.
    Falls back to configured default delivery charge for known, non-blocking issues.
    """
    site_settings = SiteSettings.get_solo()
    default_delivery_charge = Decimal(str(site_settings.default_delivery_charge))

    if not getattr(vendor, 'pathao_store_id', None):
        return {
            'amount': default_delivery_charge,
            'source': 'fallback',
            'raw': {'reason': 'Vendor has no configured Pathao store id.'},
        }

    if not getattr(address, 'city_id', None) or not getattr(address, 'zone_id', None):
        return {
            'amount': default_delivery_charge,
            'source': 'fallback',
            'raw': {'reason': 'Address is missing Pathao city/zone mapping.'},
        }

    try:
        access_token = get_access_token()
        raw_price_data = get_price_plan(
            access_token=access_token,
            store_id=int(vendor.pathao_store_id),
            item_type=int(item_type),
            delivery_type=int(delivery_type),
            item_weight=float(item_weight),
            recipient_city=int(address.city_id),
            recipient_zone=int(address.zone_id),
        )
        amount = extract_delivery_amount(raw_price_data)
        return {'amount': amount, 'source': 'pathao', 'raw': raw_price_data}
    except Exception as exc:
        return {
            'amount': default_delivery_charge,
            'source': 'fallback',
            'raw': {'reason': str(exc)},
        }
