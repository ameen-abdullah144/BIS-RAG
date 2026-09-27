import sys
import re
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))

from collectors.labs import LaboratoriesCollector

def debug_collector(is_number="IS 2082:2018"):
    collector = LaboratoriesCollector()
    # Parse IS number
    is_components = collector._parse_is_number(is_number)
    doc_no = is_components["doc_no"]
    year = is_components["year"]
    part = is_components["part"]
    section = is_components["section"]
    params = {
        "is_number__doc_no": doc_no,
        "is_number__year": year,
        "is_number__part": part,
        "is_number__section": section,
        "lab__lab_name__icontains": "",
        "is_title": ""
    }
    url = f"{collector.LIMS_URL}/home/search_is_number/"
    query_string = collector._params_to_string(params)
    full_url = f"{url}?{query_string}" if query_string else url
    response = collector._http_get(full_url)
    if not response:
        print("Failed to fetch")
        return None
    html_text = response.text
    print(f"Fetched HTML length: {len(html_text)}")
    # Parse
    try:
        soup = BeautifulSoup(html_text, 'lxml')
    except Exception:
        soup = BeautifulSoup(html_text, 'html.parser')
    table = soup.find('table', id='review_lab_list')
    if not table:
        print("Table not found")
        return None
    print("Table found")
    tbody = table.find('tbody')
    if not tbody:
        print("No tbody")
        return None
    print("Tbody found")
    # Fix malformed </th> tags in tbody
    tbody_html = str(tbody)
    print(f"Tbody HTML length: {len(tbody_html)}")
    # Show a snippet of the tbody HTML to see if it contains the malformed tags
    if '</th>' in tbody_html:
        print("Tbody contains '</th>'")
    else:
        print("Tbody does NOT contain '</th>'")
    fixed_tbody_html = re.sub(r'</th>', '</td>', tbody_html)
    print(f"Fixed tbody HTML length: {len(fixed_tbody_html)}")
    # Replace the tbody in the soup
    tbody.clear()
    fixed_tbody_soup = BeautifulSoup(fixed_tbody_html, 'html.parser')
    for element in fixed_tbody_soup.contents:
        tbody.append(element)
    # Now get rows
    rows = tbody.find_all('tr')
    print(f"Number of rows in tbody after fix: {len(rows)}")
    # Process first row in detail
    if rows:
        row = rows[0]
        print("\n--- First row ---")
        row_html = str(row)
        print(f"Row HTML: {row_html}")
        fixed_row_html = re.sub(r'</th>', '</td>', row_html)
        print(f"Fixed row HTML: {fixed_row_html}")
        row_soup = BeautifulSoup(fixed_row_html, 'html.parser')
        cells = [cell for cell in row_soup.find_all(['td', 'th']) if cell.parent == row_soup]
        print(f"Number of cells: {len(cells)}")
        for i, cell in enumerate(cells):
            print(f"  Cell {i}: tag={cell.name}, text='{cell.get_text(strip=True)}'")
        if len(cells) >= 9:
            lab_name = cells[1].get_text(strip=True)
            lab_code = cells[2].get_text(strip=True)
            print(f"Lab Name: '{lab_name}'")
            print(f"OSL Code: '{lab_code}'")
        else:
            print("Less than 9 cells")
    # Also, let's see what the raw HTML of the tbody looks like before and after fix by extracting a known pattern
    # We know that the first row should contain "Samridhi Test House Pvt. Ltd." and "8184706"
    # Let's search for these in the original tbody HTML
    if "Samridhi Test House" in tbody_html:
        print("\nFound 'Samridhi Test House' in original tbody HTML")
    else:
        print("\nDid NOT find 'Samridhi Test House' in original tbody HTML")
    if "8184706" in tbody_html:
        print("Found '8184706' in original tbody HTML")
    else:
        print("Did NOT find '8184706' in original tbody HTML")
    # Let's see what the fixed tbody HTML looks like around where we expect the data
    # We'll just print a snippet around where we think the first row is
    # Find the first <tr> in the fixed tbody HTML
    first_tr_pos = fixed_tbody_html.find('<tr')
    if first_tr_pos != -1:
        snippet = fixed_tbody_html[first_tr_pos:first_tr_pos+2000]
        print(f"\nSnippet of fixed tbody HTML starting at first <tr>:\n{snippet}")

if __name__ == "__main__":
    debug_collector()