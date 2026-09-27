import requests
import json

# Test the API call that's failing
url = "https://standardsadmin.bis.gov.in/review-service/getProductManualDetails"

# Try payload from debug_api.py
payload1 = {
    "standardId": 18707,
    "fromPage": "guestUserPage",
    "token": None,
    "refreshToken": None,
    "clientId": None,
    "clientSecret": None,
    "sub": None
}

print("Testing payload 1 (standardId):")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload1, indent=2)}")

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

try:
    resp = requests.post(url, json=payload1, headers=headers, timeout=30)
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*50 + "\n")

# Try payload from debug_api2.py with standardEncId
payload2 = {
    "standardEncId": "eyJpdiI6ImovR1VjT0hDa0RNSENXYTNBUUd3amc9PSIsInZhbHVlIjoidWkvaTJwQ2ZMUGp6WUpGK0pMRE0wdz09IiwibWFjIjoiYWEzODQ4MTc4NzM5ZDIxMDU0Y2JhNWU1ZWQ3ZDRlYTA3ZjMyMzIzN2EyZWJiODIxYzZlN2U5NDNjY2RmN2U2NyIsInRhZyI6IiJ9",
    "fromPage": "guestUserPage",
    "token": None,
    "refreshToken": None,
    "clientId": None,
    "clientSecret": None,
    "sub": None
}

print("Testing payload 2 (standardEncId):")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload2, indent=2)}")

try:
    resp = requests.post(url, json=payload2, headers=headers, timeout=30)
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*50 + "\n")

# Try the third approach from debug_api2.py
payload3 = {
    "standardId": "eyJpdiI6ImovR1VjT0hDa0RNSENXYTNBUUd3amc9PSIsInZhbHVlIjoidWkvaTJwQ2ZMUGp6WUpGK0pMRE0wdz09IiwibWFjIjoiYWEzODQ4MTc4NzM5ZDIxMDU0Y2JhNWU1ZWQ3ZDRlYTA3ZjMyMzIzN2EyZWJiODIxYzZlN2U5NDNjY2RmN2U2NyIsInRhZyI6IiJ9",
    "fromPage": "guestUserPage",
    "token": None,
    "refreshToken": None,
    "clientId": None,
    "clientSecret": None,
    "sub": None
}

print("Testing payload 3 (encrypted string in standardId):")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload3, indent=2)}")

try:
    resp = requests.post(url, json=payload3, headers=headers, timeout=30)
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")