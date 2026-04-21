import requests

API_BASE = "http://localhost:8002"
payload = {
    "park_id": "MagicKingdomWaltDisneyWorld",
    "user_location": [28.3772, -81.5707],
    "party_composition": {
        "members": [
            {
                "name": "Test Adult",
                "height_inches": 68,
                "age": 30,
                "motion_sensitive": False
            }
        ]
    }
}

try:
    response = requests.post(f"{API_BASE}/get_next_action", json=payload, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")