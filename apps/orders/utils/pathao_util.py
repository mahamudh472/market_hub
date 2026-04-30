from django.conf import settings
import requests

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

'''
curl --location '{{base_url}}/aladdin/api/v1/stores' \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer {{access_token}}' \
  --data '{
   "name": "Demo Store",
   "contact_name": "Test Merchant",
   "contact_number": "017XXXXXXXX",
   "secondary_contact": "015XXXXXXXX",
   "otp_number": "017XXXXXXXX",
   "address": "House 123, Road 4, Sector 10, Uttara, Dhaka-1230, Bangladesh",
   "city_id": {{city_id}},
   "zone_id": {{zone_id}},
   "area_id": {{area_id}}
  }'
'''
def create_store(access_token, name, contact_name, contact_number, secondary_contact, otp_number, address, city_id, zone_id, area_id):
    base_url = settings.PATHAO_API_BASE_URL
    url = f"{base_url}/aladdin/api/v1/stores"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": name,
        "contact_name": contact_name,
        "contact_number": contact_number,
        "secondary_contact": secondary_contact,
        "otp_number": otp_number,
        "address": address,
        "city_id": city_id,
        "zone_id": zone_id,
        "area_id": area_id
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()['data']
    else:
        raise Exception(f"Failed to create store: {response.text}")

'''
curl --location '{{base_url}}/aladdin/api/v1/stores' \
  --header 'Content-Type: application/json; charset=UTF-8' \
  --header 'Authorization: Bearer {{access_token}}', \
  --data ''
'''
def get_stores(access_token):
    base_url = settings.PATHAO_API_BASE_URL
    url = f"{base_url}/aladdin/api/v1/stores"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['data'].get("data", [])
    else:
        raise Exception(f"Failed to get stores: {response.text}")


'''
curl --location '{{base_url}}/aladdin/api/v1/merchant/price-plan'
  --header 'Content-Type: application/json; charset=UTF-8'
  --header 'Authorization: Bearer {{issue_token}}'
  --data '{
   "store_id": "{{merchant_store_id}}",
   "item_type": 2,
   "delivery_type": 48,
   "item_weight": 0.5,
   "recipient_city": {{city_id}},
   "recipient_zone": {{zone_id}}
  }'
'''
def get_price_plan(access_token, store_id, item_type, delivery_type, item_weight, recipient_city, recipient_zone):
    base_url = settings.PATHAO_API_BASE_URL
    url = f"{base_url}/aladdin/api/v1/merchant/price-plan"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    payload = {
        "store_id": store_id,
        "item_type": item_type,
        "delivery_type": delivery_type,
        "item_weight": item_weight,
        "recipient_city": recipient_city,
        "recipient_zone": recipient_zone
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()['data']
    else:
        raise Exception(f"Failed to get price plan: {response.text}")
