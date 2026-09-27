import requests

url = "https://standardsadmin.bis.gov.in/review-service/getProductManualDetails"
payload = {
    "standardId": 18707,
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
print(resp.status_code)
print(resp.text)
