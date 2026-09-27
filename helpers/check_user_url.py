import requests
import hashlib
from pathlib import Path

def check_url():
    url = "https://www.bis.gov.in/wp-content/uploads/2019/05/Revised-PRODUCT-MANUAL-FOR-2082.pdf"
    print(f"Checking URL: {url}")

    try:
        response = requests.get(url, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
        print(f"Content-Length: {len(response.content)} bytes")

        if response.status_code == 200:
            content = response.content
            is_pdf = content.startswith(b'%PDF') if len(content) >= 4 else False
            print(f"Is PDF (signature): {is_pdf}")

            if is_pdf:
                # Save to check location
                save_dir = Path("storage/data/IS_2082/documents/check")
                save_dir.mkdir(parents=True, exist_ok=True)
                save_path = save_dir / "Revised-PRODUCT-MANUAL-FOR-2082.pdf"

                with open(save_path, "wb") as f:
                    f.write(content)

                hash_obj = hashlib.sha256(content)
                print(f"SHA-256: {hash_obj.hexdigest()}")
                print(f"File saved to: {save_path}")

                # Try to get basic PDF info
                if b'/Pages' in content[:1000]:
                    print("PDF contains /Pages indicator (good sign)")
                else:
                    print("Warning: No /Pages indicator in first 1000 bytes")

            else:
                print("Not a PDF file")
                print(f"First 200 bytes: {response.content[:200]}")
        else:
            print(f"HTTP Error: {response.status_code}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_url()