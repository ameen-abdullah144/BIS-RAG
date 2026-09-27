import requests

url = "https://standardsadmin.bis.gov.in/review-service/getProductManualDetails"
# Try using standardEncId instead
payload = {
    "standardEncId": "eyJpdiI6ImovR1VjT0hDa0RNSENXYTNBUUd3amc9PSIsInZhbHVlIjoidWkvaTJwQ2ZMUGp6WUpGK0pMRE0wdz09IiwibWFjIjoiYWEzODQ4MTc4NzM5ZDIxMDU0Y2JhNWU1ZWQ3ZDRlYTA3ZjMyMzIzN2EyZWJiODIxYzZlN2U5NDNjY2RmN2U2NyIsInRhZyI6IiJ9",
    "fromPage": "guestUserPage",
    "token": None,
    "refreshToken": None,
    "clientId": None,
    "clientSecret": None,
    "sub": None
}
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

resp = requests.post(url, json=payload, headers=headers)
print("With standardEncId:")
print(resp.status_code)
print(resp.text)

# Try passing encrypted ID to standardId field
payload2 = payload.copy()
del payload2["standardEncId"]
payload2["standardId"] = "eyJpdiI6ImovR1VjT0hDa0RNSENXYTNBUUd3amc9PSIsInZhbHVlIjoidWkvaTJwQ2ZMUGp6WUpGK0pMRE0wdz09IiwibWFjIjoiYWEzODQ4MTc4NzM5ZDIxMDU0Y2JhNWU1ZWQ3ZDRlYTA3ZjMyMzIzN2EyZWJiODIxYzZlN2U5NDNjY2RmN2U2NyIsInRhZyI6IiJ9"

resp2 = requests.post(url, json=payload2, headers=headers)
print("\nWith encrypted string in standardId:")
print(resp2.status_code)
print(resp2.text)
