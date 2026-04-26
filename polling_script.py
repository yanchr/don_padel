import requests
from datetime import datetime, date

TENANT_ID = "your-club-tenant-id"  # find this in any network request
TOKEN = "your-bearer-token"
DATE = date.today().isoformat()

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "X-Requested-With": "com.playtomic.app 6.13.0",
    "User-Agent": "iOS 18.3.1",
    "Accept": "application/json",
}

params = {
    "sport_id": "PADEL",
    "start_min": f"{DATE}T00:00:00",
    "start_max": f"{DATE}T23:59:59",
    "tenant_id": TENANT_ID,
}

resp = requests.get("https://api.playtomic.io/v1/availability", headers=headers, params=params)
print(resp.json())