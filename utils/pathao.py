
from django.conf import settings
import requests
from orders.models import PathaoCity, PathaoZone, PathaoArea, PathaoSyncProgress

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
    response = requests.get(url, headers=headers)
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
        ongoing_sync = PathaoSyncProgress.objects.filter(status='in_progress').first()
        if not ongoing_sync:
            sync_progress = PathaoSyncProgress.objects.create(status='in_progress')
            cities = get_cities(access_token)
            sync_progress.total_cities = len(cities)
            sync_progress.cities = cities
            sync_progress.status = 'in_progress'
            sync_progress.save()
        else:
            print("Resuming ongoing Pathao sync...")  # Debug log
            sync_progress = ongoing_sync
            cities = sync_progress.cities
            sync_progress.status = 'in_progress'
            sync_progress.save()

        print(f"Fetched {len(cities)} cities from Pathao API")  # Debug log
        progress = 0
        for city in cities:
            if city['city_id'] in sync_progress.synced_cities_ids:
                progress += 1
                print(f"Skipping already synced city: {city['city_name']}")  # Debug log
                continue
            progress += 1
            print(f"Processing city {progress}/{len(cities)}: {city['city_name']}")  # Progress log
            city_obj, created = PathaoCity.objects.update_or_create(
                city_id=city['city_id'],
                defaults={'city_name': city['city_name']}
            )
            zones = get_zones(access_token, city['city_id'])
            print(f"Fetched {len(zones)} zones for city {city['city_name']}")  # Debug log
            for zone in zones:
                if zone['zone_id'] in sync_progress.synced_zones_ids:
                    print(f"Skipping already synced zone: {zone['zone_name']}")  # Debug log
                    continue
                zone_obj, created = PathaoZone.objects.update_or_create(
                    zone_id=zone['zone_id'],
                    defaults={'zone_name': zone['zone_name'], 'city': city_obj}
                )
                sync_progress.synced_zones_ids.append(zone['zone_id'])
                sync_progress.save()

                areas = get_areas(access_token, zone['zone_id'])
                print(f"Fetched {len(areas)} areas for zone {zone['zone_name']}")  # Debug log
                for area in areas:
                    PathaoArea.objects.update_or_create(
                        area_id=area['area_id'],
                        defaults={'area_name': area['area_name'], 'zone': zone_obj}
                    )
                    sync_progress.synced_areas_ids.append(area['area_id'])
                    sync_progress.save()
                sync_progress.synced_zones_ids.append(zone['zone_id'])
                sync_progress.save()

            sync_progress.synced_cities_ids.append(city['city_id'])
            sync_progress.save()

        sync_progress.status = 'completed'
        sync_progress.save()
        print("Pathao data updated successfully.")
    except Exception as e:
        print(f"Error updating Pathao data: {e}")
        print("Retrying in 1 mininute...")
        import time
        time.sleep(60)  # Sleep for 1 minute before retrying
        update_pathao_data()

