import requests

path = "BisProd/bisProd/Standard_Review/Standard_Product_Manual/product_manual_68a58a49b8ccf1755679305_20082025141145_68a58a49b8ccf1755679305.pdf"

# Strategy 1: append to standardsadmin
url1 = f"https://standardsadmin.bis.gov.in/{path}"
resp1 = requests.head(url1)
print(f"URL1: {resp1.status_code}")

# Strategy 2: Oracle Cloud base (common BIS pattern)
url2 = f"https://bmqsdqljvwgm.compat.objectstorage.ap-mumbai-1.oraclecloud.com/n/bmqsdqljvwgm/b/bis_storage/o/{path}"
resp2 = requests.head(url2)
print(f"URL2: {resp2.status_code}")

# Strategy 3: Just the object storage domain
url3 = f"https://bmqsdqljvwgm.compat.objectstorage.ap-mumbai-1.oraclecloud.com/{path}"
resp3 = requests.head(url3)
print(f"URL3: {resp3.status_code}")
