import json

from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import PathaoCity, PathaoZone, PathaoArea


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
