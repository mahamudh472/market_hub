from collections import defaultdict
from decimal import Decimal

from django.db import transaction

from apps.orders.models import Order, SubOrder, OrderItem, Payment
from apps.orders.models import SiteSettings
from .helpers import (
    _quantize_money, _address_snapshot, _variant_snapshot,
    _build_discount_allocation, _calculate_tax,
)
from apps.orders.utils.ssl_commerz_util import initiate_sslcommerz_payment
from apps.orders.utils.delivery_charge import calculate_delivery_charge_for_vendor


class CheckoutError(Exception):
    """Raised for expected business-rule failures during checkout."""
    def __init__(self, message, status=400):
        self.message = message
        self.status = status
        super().__init__(message)


class CheckoutService:
    def __init__(self, user, address, cart, payment_type, request=None):
        self.user = user
        self.address = address
        self.cart = cart
        self.payment_type = payment_type
        self.request = request
        self.site_settings = SiteSettings.get_solo()

    @transaction.atomic
    def execute(self):
        self._validate_address()
        self._validate_cart()
        self._validate_cod()
        self._validate_stock()

        cart_items = self._get_cart_items()
        subtotal = self._calculate_subtotal(cart_items)
        total_discount = _quantize_money(self.cart.get_discount())
        vendor_rows = self._build_vendor_rows(cart_items, subtotal)
        discount_by_vendor = _build_discount_allocation(vendor_rows, total_discount, subtotal)

        order = self._create_parent_order(subtotal, total_discount)
        self._create_sub_orders(order, vendor_rows, discount_by_vendor)
        self._finalize_order(order)

        payment = self._create_payment(order)
        payment_url = self._handle_payment_session(order, payment)

        self._apply_voucher()
        self._clear_cart()

        return order, payment_url

    # ------------------------------------------------------------------ #
    # Validation                                                           #
    # ------------------------------------------------------------------ #

    def _validate_address(self):
        if not self.address.city_id or not self.address.zone_id:
            raise CheckoutError('Selected address must have Pathao city and zone.')

    def _validate_cart(self):
        if not self.cart or not self.cart.items.exists():
            raise CheckoutError('Cart is empty.')

    def _validate_cod(self):
        if self.payment_type == 'cod' and not self.site_settings.is_cod_enabled:
            raise CheckoutError('COD is currently disabled.')

    def _validate_stock(self):
        for item in self._get_cart_items():
            stock = item.variant.stock if item.variant else item.product.stock
            if item.quantity > stock:
                raise CheckoutError(
                    f'Insufficient stock for {item.product.name}. Available: {stock}.'
                )

    # ------------------------------------------------------------------ #
    # Cart helpers                                                         #
    # ------------------------------------------------------------------ #

    def _get_cart_items(self):
        if not hasattr(self, '_cart_items'):
            self._cart_items = list(
                self.cart.items
                .select_related('product__vendor', 'variant')
                .all()
            )
        return self._cart_items

    def _calculate_subtotal(self, cart_items):
        return _quantize_money(
            sum((item.total_price for item in cart_items), Decimal('0'))
        )

    # ------------------------------------------------------------------ #
    # Vendor rows                                                          #
    # ------------------------------------------------------------------ #

    def _build_vendor_rows(self, cart_items, subtotal):
        vendor_grouped = defaultdict(list)
        for item in cart_items:
            vendor_grouped[item.product.vendor_id].append(item)

        rows = []
        for items in vendor_grouped.values():
            vendor = items[0].product.vendor
            vendor_subtotal = _quantize_money(
                sum((line.total_price for line in items), Decimal('0'))
            )
            delivery_charge = self._calculate_delivery(vendor, items, subtotal)
            rows.append({
                'vendor': vendor,
                'items': items,
                'subtotal': vendor_subtotal,
                'delivery_charge': delivery_charge,
                'delivery_meta': self._get_delivery_meta(vendor, items),
            })
        return rows

    def _calculate_delivery(self, vendor, items, subtotal):
        free_threshold = Decimal(str(self.site_settings.free_delivery_min_order))
        if free_threshold > Decimal('0') and subtotal >= free_threshold:
            return Decimal('0.00')

        total_qty = sum(item.quantity for item in items)
        total_weight = max(0.5, float(total_qty) * 0.2)
        result = calculate_delivery_charge_for_vendor(
            vendor=vendor, address=self.address, item_weight=total_weight
        )
        return _quantize_money(result['amount'])

    def _get_delivery_meta(self, vendor, items):
        total_qty = sum(item.quantity for item in items)
        total_weight = max(0.5, float(total_qty) * 0.2)
        return calculate_delivery_charge_for_vendor(
            vendor=vendor, address=self.address, item_weight=total_weight
        )

    # ------------------------------------------------------------------ #
    # Order creation                                                       #
    # ------------------------------------------------------------------ #

    def _is_confirmed(self):
        return self.payment_type == 'cod'

    def _create_parent_order(self, subtotal, total_discount):
        cod_charge = _quantize_money(
            self.site_settings.cod_fee if self.payment_type == 'cod' else 0
        )
        return Order.objects.create(
            user=self.user,
            delivery_address=self.address,
            delivery_address_snapshot=_address_snapshot(self.address),
            voucher_code=self.cart.voucher.code if self.cart.voucher else None,
            voucher_discount=total_discount,
            subtotal=subtotal,
            tax=Decimal('0.00'),
            delivery_charge=Decimal('0.00'),
            platform_fee=Decimal('0.00'),
            cod_charge=cod_charge,
            total=Decimal('0.00'),
            status='confirmed' if self._is_confirmed() else 'pending',
        )

    def _create_sub_orders(self, order, vendor_rows, discount_by_vendor):
        tax_percent = Decimal(str(self.site_settings.tax_percent))
        platform_fee = _quantize_money(self.site_settings.platform_fee)

        self._totals = {'tax': Decimal('0'), 'delivery': Decimal('0'),
                        'platform_fee': Decimal('0'), 'total': Decimal('0')}

        for row in vendor_rows:
            vendor = row['vendor']
            vendor_discount = discount_by_vendor.get(vendor.id, Decimal('0.00'))
            taxable = _quantize_money(max(row['subtotal'] - vendor_discount, Decimal('0')))
            vendor_tax = _calculate_tax(taxable, tax_percent)
            vendor_total = _quantize_money(
                taxable + vendor_tax + row['delivery_charge'] + platform_fee
            )

            sub_order = SubOrder.objects.create(
                parent_order=order,
                vendor=vendor,
                subtotal=row['subtotal'],
                voucher_discount=vendor_discount,
                tax=vendor_tax,
                delivery_charge=row['delivery_charge'],
                platform_fee=platform_fee,
                total=vendor_total,
                status='confirmed' if self._is_confirmed() else 'pending',
                note=(
                    f"delivery_source={row['delivery_meta']['source']}; "
                    f"delivery_raw={row['delivery_meta']['raw']}"
                ),
            )

            self._create_order_items(order, sub_order, vendor, row['items'])

            self._totals['tax'] += vendor_tax
            self._totals['delivery'] += row['delivery_charge']
            self._totals['platform_fee'] += platform_fee
            self._totals['total'] += vendor_total

    def _create_order_items(self, order, sub_order, vendor, cart_items):
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                sub_order=sub_order,
                vendor=vendor,
                product=cart_item.product,
                variant=cart_item.variant,
                product_name=cart_item.product.name,
                variant_details=_variant_snapshot(cart_item.variant),
                unit_price=_quantize_money(cart_item.unit_price),
                quantity=cart_item.quantity,
                total_price=_quantize_money(cart_item.total_price),
                status='confirmed' if self._is_confirmed() else 'pending',
            )
            self._deduct_stock(cart_item)

    def _deduct_stock(self, cart_item):
        if cart_item.variant:
            cart_item.variant.stock = max(0, cart_item.variant.stock - cart_item.quantity)
            cart_item.variant.save(update_fields=['stock'])
        else:
            cart_item.product.stock = max(0, cart_item.product.stock - cart_item.quantity)
            cart_item.product.save(update_fields=['stock'])

    def _finalize_order(self, order):
        cod_charge = order.cod_charge
        order.tax = _quantize_money(self._totals['tax'])
        order.delivery_charge = _quantize_money(self._totals['delivery'])
        order.platform_fee = _quantize_money(self._totals['platform_fee'])
        order.total = _quantize_money(self._totals['total'] + cod_charge)
        order.save(update_fields=['tax', 'delivery_charge', 'platform_fee', 'cod_charge', 'total', 'updated_at'])

    # ------------------------------------------------------------------ #
    # Payment                                                              #
    # ------------------------------------------------------------------ #

    def _create_payment(self, order):
        return Payment.objects.create(
            order=order,
            method='cod' if self.payment_type == 'cod' else 'online',
            status='pending',
            amount=order.total,
        )

    def _handle_payment_session(self, order, payment):
        if self.payment_type != 'paynow':
            return None

        try:
            session = initiate_sslcommerz_payment(
                request=self.request,
                order=order,
                address_snapshot=order.delivery_address_snapshot or {},
            )
            payment.transaction_id = session['transaction_id']
            payment.gateway_response = session['gateway_response']
            payment.save(update_fields=['transaction_id', 'gateway_response'])
            return session['payment_url']
        except Exception as exc:
            transaction.set_rollback(True)
            raise CheckoutError(f'Could not create payment session: {exc}')

    # ------------------------------------------------------------------ #
    # Post-order cleanup                                                   #
    # ------------------------------------------------------------------ #

    def _apply_voucher(self):
        from apps.cart.models import VoucherUsage
        if not self.cart.voucher:
            return
        voucher = self.cart.voucher
        VoucherUsage.objects.create(voucher=voucher, user=self.user)
        voucher.used_count += 1
        voucher.save(update_fields=['used_count'])

    def _clear_cart(self):
        self.cart.items.all().delete()
        self.cart.voucher = None
        self.cart.save(update_fields=['voucher', 'updated_at'])
