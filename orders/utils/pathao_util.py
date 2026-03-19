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
    else:        raise Exception(f"Failed to get cities: {response.text}")
