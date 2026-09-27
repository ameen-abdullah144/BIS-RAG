import requests
import hashlib
from pathlib import Path

def test_pdf_download():
    print("Testing PDF download strategies for IS 2082 product manual")
    print("=" * 60)

    # Base information from metadata
    file_path = "BisProd/bisProd/Standard_Review/Standard_Product_Manual/product_manual_68a58a49b8ccf1755679305_20082025141145_68a58a49b8ccf1755679305.pdf"
    file_name = "product_manual_68a58a49b8ccf1755679305_20082025141145_68a58a49b8ccf1755679305.pdf"

    print(f"File path from API: {file_path}")
    print(f"File name: {file_name}")
    print()

    # Strategy 1: append to standardsadmin (from debug_api3.py)
    url1 = f"https://standardsadmin.bis.gov.in/{file_path}"
    print(f"Strategy 1 - StandardsAdmin direct: {url1}")

    # Strategy 2: Oracle Cloud base (from debug_api3.py)
    url2 = f"https://bmqsdqljvwgm.compat.objectstorage.ap-mumbai-1.oraclecloud.com/n/bmqsdqljvwgm/b/bis_storage/o/{file_path}"
    print(f"Strategy 2 - Oracle Cloud with bucket: {url2}")

    # Strategy 3: Just the object storage domain (from debug_api3.py)
    url3 = f"https://bmqsdqljvwgm.compat.objectstorage.ap-mumbai-1.oraclecloud.com/{file_path}"
    print(f"Strategy 3 - Object storage domain: {url3}")

    # Strategy 4: Try bis.gov.in domain
    url4 = f"https://www.bis.gov.in/{file_path}"
    print(f"Strategy 4 - BIS main domain: {url4}")

    # Strategy 5: Try standards.bis.gov.in
    url5 = f"https://standards.bis.gov.in/{file_path}"
    print(f"Strategy 5 - Standards domain: {url5}")

    urls = [
        ("Strategy 1 - StandardsAdmin", url1),
        ("Strategy 2 - Oracle Cloud w/ bucket", url2),
        ("Strategy 3 - Object storage domain", url3),
        ("Strategy 4 - BIS main domain", url4),
        ("Strategy 5 - Standards domain", url5)
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*"
    }

    for strategy_name, url in urls:
        print(f"\n{strategy_name}:")
        print(f"  URL: {url}")

        try:
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            print(f"  Status Code: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('content-type', 'unknown')}")
            print(f"  Content-Length: {response.headers.get('content-length', 'unknown')}")

            if response.status_code == 200:
                # Check if it's actually a PDF
                content_type = response.headers.get('content-type', '').lower()
                is_pdf = 'pdf' in content_type

                # Download first few bytes to check PDF signature
                content = response.content
                is_pdf_by_signature = content.startswith(b'%PDF') if len(content) >= 4 else False

                print(f"  Is PDF (content-type): {is_pdf}")
                print(f"  Is PDF (signature): {is_pdf_by_signature}")
                print(f"  Content length: {len(content)} bytes")

                if len(content) > 0:
                    # Show first 100 chars as text to see what we got
                    preview = content[:100].decode('utf-8', errors='ignore')
                    print(f"  Preview: {repr(preview)}")

                if is_pdf or is_pdf_by_signature:
                    print(f"  ✅ SUCCESS: Got actual PDF content!")

                    # Save to test location
                    test_dir = Path("storage/data/IS_2082/documents/test")
                    test_dir.mkdir(parents=True, exist_ok=True)
                    test_file = test_dir / f"{strategy_name.replace(' ', '_').replace('-', '_')}.pdf"

                    with open(test_file, 'wb') as f:
                        f.write(content)

                    # Compute hash
                    hash_obj = hashlib.sha256(content)
                    print(f"  SHA-256: {hash_obj.hexdigest()}")

                    return {
                        'strategy': strategy_name,
                        'url': url,
                        'content': content,
                        'hash': hash_obj.hexdigest(),
                        'length': len(content)
                    }
                else:
                    print(f"  ❌ FAILED: Got {content_type} instead of PDF")
                    if len(content) < 200:
                        print(f"  Content: {content}")
            else:
                print(f"  ❌ FAILED: HTTP {response.status_code}")

        except Exception as e:
            print(f"  ❌ ERROR: {e}")

    print("\n" + "=" * 60)
    print("No strategy returned a valid PDF file")
    return None

if __name__ == "__main__":
    result = test_pdf_download()
    if result:
        print(f"\n🎯 SUCCESSFUL STRATEGY: {result['strategy']}")
        print(f"URL: {result['url']}")
    else:
        print("\n❌ All strategies failed to retrieve a valid PDF")