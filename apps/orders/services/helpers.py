# services/helpers.py
from decimal import Decimal, ROUND_HALF_UP


MONEY_QUANT = Decimal('0.01')

def _quantize_money(value):
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _calculate_tax(amount_after_discount, tax_percent):
    if amount_after_discount <= Decimal('0'):
        return Decimal('0.00')
    return _quantize_money(amount_after_discount * (tax_percent / Decimal('100')))


def _address_snapshot(address):
    return {
        'id': address.id,
        'label': address.label,
        'full_name': address.full_name,
        'phone_number': address.phone_number,
        'address': address.address,
        'landmark': address.landmark,
        'postal_code': address.postal_code,
        'country': address.country,
        'city_id': address.city_id,
        'city_name': address.city.city_name if address.city else None,
        'zone_id': address.zone_id,
        'zone_name': address.zone.zone_name if address.zone else None,
        'area_id': address.area_id,
        'area_name': address.area.area_name if address.area else None,
    }


def _variant_snapshot(variant):
    if not variant:
        return None
    return {
        'id': str(variant.id),
        'options': {
            option.variant_type.name: option.value
            for option in variant.options.select_related('variant_type').all()
        },
    }


def _build_discount_allocation(vendor_rows, total_discount, total_subtotal):
    if total_discount <= Decimal('0') or total_subtotal <= Decimal('0'):
        return {row['vendor'].id: Decimal('0.00') for row in vendor_rows}

    allocations = {}
    allocated_total = Decimal('0.00')
    for row in vendor_rows:
        ratio = row['subtotal'] / total_subtotal
        discount = _quantize_money(total_discount * ratio)
        allocations[row['vendor'].id] = discount
        allocated_total += discount

    remainder = _quantize_money(total_discount - allocated_total)
    if remainder != Decimal('0.00') and vendor_rows:
        last_vendor_id = vendor_rows[-1]['vendor'].id
        allocations[last_vendor_id] = _quantize_money(allocations[last_vendor_id] + remainder)
    return allocations
