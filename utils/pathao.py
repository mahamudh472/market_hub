
from django.conf import settings
import requests
from orders.models import PathaoCity, PathaoZone, PathaoArea

def get_access_token():
    base_url = settings.PATHAO_API_BASE_URL
    url = f"{base_url}/aladdin/api/v1/issue-token"
    payload = {
        "client_id": settings.PATHAO_CLIENT_ID,
        "client_secret": settings.PATHAO_CLIENT_SECRET,
        "grant_type": "password",
        "username": settings.PATHAO_USERNAME,
        "password": settings.PATHAO_PASSWORD
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        raise Exception(f"Failed to get access token: {response.text}")

def get_cities(access_token):
    base_url = settings.PATHAO_API_BASE_URL
    url = f"{base_url}/aladdin/api/v1/city-list"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['data'].get("data", [])
    else:        
        raise Exception(f"Failed to get cities: {response.text}")

def get_zones(access_token, city_id):
    base_url = settings.PATHAO_API_BASE_URL
    url = f"{base_url}/aladdin/api/v1/cities/{city_id}/zone-list"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    print(f"Requesting zones for city_id={city_id} with URL: {url}")  # Debug log
    response = requests.get(url, headers=headers)
    print(f"Get zones response: {response.status_code} - {response.text}")  # Debug log
    if response.status_code == 200:
        return response.json()['data'].get("data", [])
    else:
        raise Exception(f"Failed to get zones: {response.text}")

def get_areas(access_token, zone_id):
    base_url = settings.PATHAO_API_BASE_URL
    url = f"{base_url}/aladdin/api/v1/zones/{zone_id}/area-list"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['data'].get("data", [])
    else:
        raise Exception(f"Failed to get areas: {response.text}")

def update_pathao_data():
    try:
        access_token = get_access_token()
        cities = get_cities(access_token)
        print(f"Fetched {len(cities)} cities from Pathao API")  # Debug log
        for city in cities:
            city_obj, created = PathaoCity.objects.update_or_create(
                city_id=city['city_id'],
                defaults={'city_name': city['city_name']}
            )
            zones = get_zones(access_token, city['city_id'])
            print(f"Fetched {len(zones)} zones for city {city['city_name']}")  # Debug log
            for zone in zones:
                zone_obj, created = PathaoZone.objects.update_or_create(
                    zone_id=zone['zone_id'],
                    defaults={'zone_name': zone['zone_name'], 'city': city_obj}
                )
                areas = get_areas(access_token, zone['zone_id'])
                print(f"Fetched {len(areas)} areas for zone {zone['zone_name']}")  # Debug log
                for area in areas:
                    PathaoArea.objects.update_or_create(
                        area_id=area['area_id'],
                        defaults={'area_name': area['area_name'], 'zone': zone_obj}
                    )
        print("Pathao data updated successfully.")
    except Exception as e:
        print(f"Error updating Pathao data: {e}")
