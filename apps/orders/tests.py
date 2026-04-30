import json
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User, UserAddress
from apps.cart.models import Cart, CartItem
from apps.products.models import Category, Product

from .models import Order, PathaoCity, PathaoZone, PathaoArea, SiteSettings


class PathaoLookupAPITests(APITestCase):
    def setUp(self):
        cache.clear()

        self.city_dhaka = PathaoCity.objects.create(city_id=1, city_name='Dhaka')
        self.city_chattogram = PathaoCity.objects.create(city_id=2, city_name='Chattogram')

        self.zone_gulshan = PathaoZone.objects.create(zone_id=10, zone_name='Gulshan', city=self.city_dhaka)
        self.zone_uttara = PathaoZone.objects.create(zone_id=11, zone_name='Uttara', city=self.city_dhaka)
        self.zone_halisahar = PathaoZone.objects.create(zone_id=20, zone_name='Halisahar', city=self.city_chattogram)

        self.area_1 = PathaoArea.objects.create(
            area_id=100,
            area_name='Gulshan 1',
            zone=self.zone_gulshan,
            home_delivery_available=True,
            pickup_available=True,
        )
        self.area_2 = PathaoArea.objects.create(
            area_id=101,
            area_name='Gulshan 2',
            zone=self.zone_gulshan,
            home_delivery_available=False,
            pickup_available=True,
        )
        self.area_3 = PathaoArea.objects.create(
            area_id=200,
            area_name='Uttara 10',
            zone=self.zone_uttara,
            home_delivery_available=True,
            pickup_available=False,
        )

    def test_city_list_returns_all_cities(self):
        response = self.client.get(reverse('pathao-city-list'))
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['count'], 2)
        self.assertEqual(
            data['results'],
            [
                {'city_id': 2, 'city_name': 'Chattogram'},
                {'city_id': 1, 'city_name': 'Dhaka'},
            ],
        )

    def test_city_list_uses_cache_on_second_request(self):
        url = reverse('pathao-city-list')
        first_response = self.client.get(url)
        first_data = json.loads(first_response.content)
        self.assertEqual(first_response.status_code, 200)

        with self.assertNumQueries(0):
            second_response = self.client.get(url)
            second_data = json.loads(second_response.content)

        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_data, first_data)

    def test_zone_list_filters_by_city_id(self):
        response = self.client.get(reverse('pathao-zone-list'), {'city_id': self.city_dhaka.city_id})
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['city_id'], self.city_dhaka.city_id)
        self.assertEqual(data['count'], 2)
        self.assertEqual(
            data['results'],
            [
                {'zone_id': 10, 'zone_name': 'Gulshan', 'city_id': 1},
                {'zone_id': 11, 'zone_name': 'Uttara', 'city_id': 1},
            ],
        )

    def test_zone_list_requires_city_id(self):
        response = self.client.get(reverse('pathao-zone-list'))
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['detail'], 'city_id query parameter is required.')

    def test_area_list_filters_by_zone_id(self):
        response = self.client.get(reverse('pathao-area-list'), {'zone_id': self.zone_gulshan.zone_id})
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['zone_id'], self.zone_gulshan.zone_id)
        self.assertEqual(data['count'], 2)
        self.assertEqual(
            data['results'],
            [
                {
                    'area_id': 100,
                    'area_name': 'Gulshan 1',
                    'zone_id': 10,
                    'home_delivery_available': True,
                    'pickup_available': True,
                },
                {
                    'area_id': 101,
                    'area_name': 'Gulshan 2',
                    'zone_id': 10,
                    'home_delivery_available': False,
                    'pickup_available': True,
                },
            ],
        )

    def test_area_list_requires_zone_id(self):
        response = self.client.get(reverse('pathao-area-list'))
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['detail'], 'zone_id query parameter is required.')


class CheckoutFlowTests(APITestCase):
    def setUp(self):
        self.city = PathaoCity.objects.create(city_id=1, city_name='Dhaka')
        self.zone = PathaoZone.objects.create(zone_id=10, zone_name='Gulshan', city=self.city)
        self.area = PathaoArea.objects.create(
            area_id=101,
            area_name='Gulshan 1',
            zone=self.zone,
            home_delivery_available=True,
            pickup_available=True,
        )

        self.customer = User.objects.create_user(
            email='checkout-customer@example.com',
            password='strong-pass',
            role=Role.CUSTOMER,
        )
        self.client.force_authenticate(user=self.customer)

        self.address = UserAddress.objects.create(
            user=self.customer,
            label='home',
            full_name='Checkout User',
            phone_number='01700000000',
            address='Road 10, Dhaka',
            city=self.city,
            zone=self.zone,
            area=self.area,
        )

        self.vendor_user_1 = User.objects.create_user(
            email='vendor-1@example.com',
            password='strong-pass',
            role=Role.VENDOR,
        )
        self.vendor_user_2 = User.objects.create_user(
            email='vendor-2@example.com',
            password='strong-pass',
            role=Role.VENDOR,
        )

        self.vendor_1 = self.vendor_user_1.vendor_profile
        self.vendor_1.name = 'Vendor One'
        self.vendor_1.pathao_store_id = '1001'
        self.vendor_1.save(update_fields=['name', 'pathao_store_id'])

        self.vendor_2 = self.vendor_user_2.vendor_profile
        self.vendor_2.name = 'Vendor Two'
        self.vendor_2.pathao_store_id = '1002'
        self.vendor_2.save(update_fields=['name', 'pathao_store_id'])

        self.category = Category.objects.create(name='Electronics')
        self.product_1 = Product.objects.create(
            vendor=self.vendor_1,
            name='Product A',
            description='A',
            price=Decimal('100'),
            stock=10,
            category=self.category,
        )
        self.product_2 = Product.objects.create(
            vendor=self.vendor_2,
            name='Product B',
            description='B',
            price=Decimal('200'),
            stock=10,
            category=self.category,
        )

        self.cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(cart=self.cart, product=self.product_1, quantity=2)
        CartItem.objects.create(cart=self.cart, product=self.product_2, quantity=1)

        SiteSettings.objects.create(
            cod_fee=Decimal('30'),
            tax_percent=Decimal('5'),
            platform_fee=Decimal('10'),
            default_delivery_charge=Decimal('60'),
            free_delivery_min_order=Decimal('0'),
        )

    @patch('orders.views.calculate_delivery_charge_for_vendor')
    def test_checkout_cod_creates_parent_and_suborders(self, mock_delivery_calc):
        mock_delivery_calc.return_value = {
            'amount': Decimal('50'),
            'source': 'pathao',
            'raw': {'price': '50'},
        }

        response = self.client.post(
            reverse('order-checkout'),
            {'address_id': self.address.id, 'payment_type': 'cod'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Order.objects.count(), 1)

        order = Order.objects.first()
        self.assertEqual(order.sub_orders.count(), 2)
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.cod_charge, Decimal('30.00'))
        self.assertEqual(order.payment.method, 'cod')
        self.assertEqual(order.payment.amount, order.total)

        for sub_order in order.sub_orders.all():
            vendors = set(sub_order.items.values_list('vendor_id', flat=True))
            self.assertEqual(len(vendors), 1)

        self.assertFalse(self.cart.items.exists())

    @patch('orders.views.initiate_sslcommerz_payment')
    @patch('orders.views.calculate_delivery_charge_for_vendor')
    def test_checkout_paynow_returns_payment_url(self, mock_delivery_calc, mock_ssl_payment):
        mock_delivery_calc.return_value = {
            'amount': Decimal('50'),
            'source': 'pathao',
            'raw': {'price': '50'},
        }
        mock_ssl_payment.return_value = {
            'payment_url': 'https://sandbox.sslcommerz.com/gwprocess/v4/example',
            'transaction_id': 'txn-123',
            'gateway_response': {'status': 'SUCCESS'},
        }

        response = self.client.post(
            reverse('order-checkout'),
            {'address_id': self.address.id, 'payment_type': 'paynow'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Order.objects.count(), 1)

        order = Order.objects.first()
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.payment.method, 'online')
        self.assertEqual(order.payment.transaction_id, 'txn-123')
        self.assertEqual(
            response.data['payment_url'],
            'https://sandbox.sslcommerz.com/gwprocess/v4/example',
        )
