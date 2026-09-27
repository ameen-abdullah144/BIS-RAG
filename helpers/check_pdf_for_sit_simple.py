import fitz  # PyMuPDF
import os

def check_pdf_for_sit_content():
    pdf_path = "storage/data/IS_2082/documents/product_manual_68a58a49b8ccf1755679305_20082025141145_68a58a49b8ccf1755679305.pdf"

    if not os.path.exists(pdf_path):
        print("ERROR: PDF file not found")
        return

    print(f"Checking PDF for SIT content: {pdf_path}")

    try:
        # Open the PDF
        doc = fitz.open(pdf_path)
        print(f"PDF opened successfully")
        print(f"Number of pages: {doc.page_count}")
        print()

        # Check each page for SIT-related content
        sit_found_pages = []
        sit_keywords = ['scheme of inspection', 'inspection and testing', 'sit ', 'sampling', 'test method']

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text = page.get_text()

            # Check for SIT-related keywords (case insensitive)
            text_lower = text.lower()
            found_keywords = [kw for kw in sit_keywords if kw in text_lower]

            if found_keywords:
                sit_found_pages.append((page_num + 1, found_keywords))  # Page numbers are 1-indexed

        doc.close()

        print("=" * 50)
        if sit_found_pages:
            print(f"SIT-related content found on pages: {[page for page, _ in sit_found_pages]}")
            if sit_found_pages:
                first_sit_page = sit_found_pages[0][0]
                print(f"First SIT content appears on page: {first_sit_page}")

                # Check if it starts from page 5 as user claimed
                if first_sit_page == 5:
                    print("CONFIRMED: SIT content starts from page 5 as claimed!")
                elif first_sit_page < 5:
                    print(f"SIT content starts earlier than claimed: page {first_sit_page}")
                else:
                    print(f"SIT content starts later than claimed: page {first_sit_page}")
        else:
            print("NO SIT-related content found in the PDF")
            print("Keywords checked: scheme of inspection, inspection and testing, sit, sampling, test method")

    except Exception as e:
        print(f"Error reading PDF: {e}")

if __name__ == "__main__":
    check_pdf_for_sit_content()