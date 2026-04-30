from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Role, User, UserAddress
from orders.models import PathaoCity, PathaoZone


class CustomerAddressCreateAPITest(APITestCase):
    def setUp(self):
        self.url = reverse('customer_profile_add_address')

        self.city = PathaoCity.objects.create(city_id=1, city_name='Dhaka')
        self.zone = PathaoZone.objects.create(zone_id=10, zone_name='Gulshan', city=self.city)

        self.customer = User.objects.create_user(
            email='customer@example.com',
            password='strong-pass',
            role=Role.CUSTOMER,
        )

        self.vendor = User.objects.create_user(
            email='vendor@example.com',
            password='strong-pass',
            role=Role.VENDOR,
        )

    def test_customer_can_add_address(self):
        self.client.force_authenticate(user=self.customer)

        payload = {
            'label': 'home',
            'full_name': 'John Doe',
            'phone_number': '01700000000',
            'address_line1': 'Road 12, House 5',
            'city': self.city.city_id,
            'zone': self.zone.zone_id,
            'is_default': True,
        }

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UserAddress.objects.filter(user=self.customer).count(), 1)
        self.assertEqual(UserAddress.objects.get(user=self.customer).zone_id, self.zone.zone_id)

    def test_non_customer_cannot_add_address(self):
        self.client.force_authenticate(user=self.vendor)

        payload = {
            'label': 'home',
            'full_name': 'Vendor User',
            'phone_number': '01800000000',
            'address_line1': 'Banani',
            'city': self.city.city_id,
            'zone': self.zone.zone_id,
        }

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(UserAddress.objects.filter(user=self.vendor).count(), 0)
