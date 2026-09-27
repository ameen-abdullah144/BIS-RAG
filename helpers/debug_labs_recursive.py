import sys
import re
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))

from collectors.labs import LaboratoriesCollector

def debug_collector(is_number="IS 2082:2018"):
    print(f"=== Debugging Laboratories Collector (recursive=False) for {is_number} ===")
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
        print("ERROR: Failed to fetch")
        return None
    html_text = response.text
    # Parse HTML response directly, trying lxml first then html.parser if table not found
    try:
        soup = BeautifulSoup(html_text, 'lxml')
        table = soup.find('table', id='review_lab_list')
    except Exception:
        soup = None
        table = None
    if table is None:
        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            table = soup.find('table', id='review_lab_list')
        except Exception:
            soup = None
            table = None
    if table is None:
        print("ERROR: No laboratory table found")
        return None
    # Get tbody
    tbody = table.find('tbody')
    if not tbody:
        print("ERROR: No tbody in table")
        return None
    # Fix malformed </th> tags in tbody: replace '</th>' with '</td>' in the tbody's HTML
    tbody_html = str(tbody)
    fixed_tbody_html = re.sub(r'</th>', '</td>', tbody_html)
    # Replace the tbody in the soup with the fixed one
    tbody.clear()
    fixed_tbody_soup = BeautifulSoup(fixed_tbody_html, 'html.parser')
    for element in fixed_tbody_soup.contents:
        tbody.append(element)
    # Get all rows from tbody (direct children only)
    rows = tbody.find_all('tr', recursive=False)
    print(f"Number of direct child rows in tbody: {len(rows)}")
    # Process first few rows
    for i, row in enumerate(rows[:5]):
        print(f"\n--- Row {i} ---")
        row_html = str(row)
        print(f"Row HTML (first 500 chars): {row_html[:500]}")
        fixed_row_html = re.sub(r'</th>', '</td>', row_html)
        print(f"Fixed row HTML (first 500 chars): {fixed_row_html[:500]}")
        row_soup = BeautifulSoup(fixed_row_html, 'html.parser')
        cells = [cell for cell in row_soup.find_all(['td', 'th']) if cell.parent == row_soup]
        print(f"Number of cells: {len(cells)}")
        for j, cell in enumerate(cells):
            print(f"  Cell {j}: tag={cell.name}, text='{cell.get_text(strip=True)}'")
        if len(cells) >= 9:
            lab_name = cell_texts[1] if len(cell_texts) > 1 else ""
            lab_code = cell_texts[2] if len(cell_texts) > 2 else ""
            print(f"  Lab Name: '{lab_name}'")
            print(f"  OSL Code: '{lab_code}'")
        else:
            print(f"  Less than 9 cells, skipping")

if __name__ == "__main__":
    debug_collector()