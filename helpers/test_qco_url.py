import json
import re
from pathlib import Path
import requests
import hashlib
from datetime import datetime

def main():
    print("Testing QCO URL construction and download")

    # Load config
    config_path = Path("config/niches/water_heaters.json")
    if not config_path.exists():
        print(f"ERROR: {config_path} not found")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    qco_ref = config.get("qco_reference")
    if not qco_ref:
        print("ERROR: qco_reference not found in config")
        return

    print(f"QCO Reference: {qco_ref}")

    # Extract published date
    published_str = qco_ref.get("published")
    if not published_str:
        print("ERROR: published date not found in qco_reference")
        return

    try:
        # Published date format: "2024-03-05"
        published_date = datetime.strptime(published_str, "%Y-%m-%d")
        year = published_date.year
        month = published_date.month
    except Exception as e:
        print(f"ERROR: failed to parse published date: {e}")
        return

    # Construct base URL
    base_url = "https://www.bis.gov.in/wp-content/uploads/"
    url_path = f"{year:04d}/{month:02d}/"

    # Create filename from title
    title = qco_ref.get("title", "")
    # Remove parentheses and comma, replace spaces with hyphens, convert to lowercase?
    # We'll try to mimic the URL we found:
    #   "Electrical-Appliances-for-domestic-water-heating-Quality-Control-Order-2023.pdf"
    # The title is: "Electrical Appliances for domestic water heating (Quality Control) Order, 2023"
    # We want to remove the parentheses and comma, and replace spaces with hyphens.
    # Also note the year in the filename is 2023, which is from the title? Actually the title has ", 2023" at the end.
    # We can extract the year from the title or use the year from the published date? The published date is 2024-03-05, but the year in the filename is 2023.
    # The gazette_id is S.O. 1253(E) and published 2024-03-05, but the title mentions 2023.
    # This is confusing.

    # Let's try to create a filename by:
    #   - Removing any text in parentheses and the comma after it.
    #   - Then replacing spaces with hyphens.
    #   - Then appending ".pdf"
    # But we saw the filename includes the year 2023 at the end.

    # Let's try to extract the year from the title if it ends with a year.
    # We'll look for a 4-digit number at the end of the title.
    year_match = re.search(r'(\d{4})$', title)
    if year_match:
        title_year = year_match.group(1)
        # Remove the year and any preceding comma and space from the title for the base
        title_without_year = title[:year_match.start()].strip()
        # Remove trailing comma and space
        title_without_year = title_without_year.rstrip(', ')
    else:
        title_year = str(year)  # fallback to the year from published date
        title_without_year = title

    # Now replace spaces with hyphens and remove any other unwanted characters
    # We'll keep only alphanumeric, hyphen, and space, then replace spaces with hyphens
    filename_base = re.sub(r'[^a-zA-Z0-9\s]', '', title_without_year)  # remove non-alnum/space
    filename_base = re.sub(r'\s+', '-', filename_base.strip())  # replace spaces with hyphens
    # Append the year (from title if found, else from published date) and .pdf
    filename = f"{filename_base}-{title_year}.pdf"

    # Construct full URL
    full_url = base_url + url_path + filename
    print(f"Constructed URL: {full_url}")

    # Try to download
    try:
        resp = requests.get(full_url, timeout=30)
        resp.raise_for_status()
        print(f"Download successful: {len(resp.content)} bytes")
    except Exception as e:
        print(f"Failed to download from constructed URL: {e}")
        # Try the URL we found from the search as a fallback
        fallback_url = "https://www.bis.gov.in/wp-content/uploads/2024/03/Electrical-Appliances-for-domestic-water-heating-Quality-Control-Order-2023.pdf"
        print(f"Trying fallback URL: {fallback_url}")
        try:
            resp = requests.get(fallback_url, timeout=30)
            resp.raise_for_status()
            print(f"Fallback download successful: {len(resp.content)} bytes")
            full_url = fallback_url
        except Exception as e2:
            print(f"Fallback also failed: {e2}")
            return

    # Verify it's a PDF by checking the first few bytes
    if resp.content[:4] == b'%PDF':
        print("File appears to be a valid PDF (starts with %PDF)")
    else:
        print("WARNING: File does not start with %PDF")

    # Compute SHA-256
    sha256 = hashlib.sha256(resp.content).hexdigest()
    print(f"SHA-256: {sha256}")

    # Save to a temporary location for inspection
    temp_path = Path("temp_qco.pdf")
    with open(temp_path, "wb") as f:
        f.write(resp.content)
    print(f"Saved to {temp_path}")

    # Try to extract some text to verify it's the QCO gazette
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(temp_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        # Check for key phrases
        if "Electrical Appliances for domestic water heating" in text and "Quality Control" in text:
            print("PDF contains expected title phrases")
        else:
            print("WARNING: PDF may not contain expected title phrases")
        # Check for gazette_id
        if "S.O. 1253(E)" in text:
            print("PDF contains gazette ID: S.O. 1253(E)")
        else:
            print("WARNING: PDF may not contain gazette ID")
    except ImportError:
        print("PyMuPDF not installed, skipping text extraction")
    except Exception as e:
        print(f"Error extracting text: {e}")

if __name__ == "__main__":
    main()