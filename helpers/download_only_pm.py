import requests
import hashlib
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    print("Downloading REAL Product Manual for IS 2082 (file only)")
    print("=" * 60)

    # The verified working URL from our tests
    file_path = "BisProd/bisProd/Standard_Review/Standard_Product_Manual/product_manual_68a58a49b8ccf1755679305_20082025141145_68a58a49b8ccf1755679305.pdf"
    download_url = f"https://bmqsdqljvwgm.compat.objectstorage.ap-mumbai-1.oraclecloud.com/{file_path}"

    print(f"Download URL: {download_url}")

    # Set up save location
    save_dir = Path("storage/data/IS_2082/documents")
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / Path(file_path).name

    print(f"Saving to: {save_path}")

    try:
        # Download the file
        response = requests.get(download_url, timeout=60)
        response.raise_for_status()

        # Verify it's a PDF
        content_type = response.headers.get('content-type', '').lower()
        is_pdf = 'pdf' in content_type
        content = response.content
        is_pdf_by_signature = content.startswith(b'%PDF') if len(content) >= 4 else False

        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {content_type}")
        print(f"Is PDF (content-type): {is_pdf}")
        print(f"Is PDF (signature): {is_pdf_by_signature}")
        print(f"Content-Length: {len(content)} bytes")

        if is_pdf or is_pdf_by_signature:
            # Save the file
            with open(save_path, "wb") as f:
                f.write(content)

            # Compute hash
            hash_obj = hashlib.sha256(content)
            print(f"SHA-256: {hash_obj.hexdigest()}")
            print(f"File saved successfully!")

            # Verify the saved file
            if save_path.exists():
                file_size = save_path.stat().st_size
                print(f"Verified file size: {file_size} bytes")

                # Quick sanity check - read first few bytes
                with open(save_path, "rb") as f:
                    first_bytes = f.read(20)
                    print(f"First 20 bytes: {first_bytes}")

                return True
            else:
                print("ERROR: File was not saved correctly")
                return False
        else:
            print("ERROR: Downloaded content is not a PDF")
            print(f"First 200 bytes: {content[:200]}")
            return False

    except Exception as e:
        print(f"ERROR: Failed to download file: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ DOWNLOAD SUCCESSFUL - Real PDF obtained and saved")
    else:
        print("\n❌ DOWNLOAD FAILED")