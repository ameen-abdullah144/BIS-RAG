import sys
import re
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))

from collectors.labs import LaboratoriesCollector

def debug_tbody(is_number="IS 2082:2018"):
    collector = LaboratoriesCollector()
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
        return
    html_text = response.text
    # Parse with html.parser (since lxml didn't find table)
    soup = BeautifulSoup(html_text, 'html.parser')
    table = soup.find('table', id='review_lab_list')
    if not table:
        print("Table not found")
        return
    tbody = table.find('tbody')
    if not tbody:
        print("No tbody")
        return
    print(f"Tbody tag: {tbody.name}")
    print(f"Tbody attributes: {tbody.attrs}")
    print("\nChildren of tbody:")
    for i, child in enumerate(tbody.children):
        print(f"  Child {i}: {child}")
        if hasattr(child, 'name'):
            print(f"    name: {child.name}")
            if child.name == 'tr':
                print(f"    This is a tr")
            else:
                print(f"    Not a tr")
        # Print first 200 chars of child if it's a tag
        if hasattr(child, '__str__'):
            child_str = str(child)
            if len(child_str) > 200:
                print(f"    String (first 200): {child_str[:200]}...")
            else:
                print(f"    String: {child_str}")
    # Now fix the tbody
    tbody_html = str(tbody)
    print(f"\nTbody HTML length: {len(tbody_html)}")
    # Look for <tr> in the tbody HTML
    tr_matches = re.findall(r'<tr[^>]*>', tbody_html, re.IGNORECASE)
    print(f"Number of <tr> tags in tbody HTML (regex): {len(tr_matches)}")
    if tr_matches:
        print(f"First few <tr> matches: {tr_matches[:5]}")
    # Fix malformed tags
    fixed_tbody_html = re.sub(r'</th>', '</td>', tbody_html)
    print(f"Fixed tbody HTML length: {len(fixed_tbody_html)}")
    # Parse the fixed tbody HTML
    fixed_soup = BeautifulSoup(fixed_tbody_html, 'html.parser')
    # The fixed_soup should be a tbody element (since we passed the whole tbox)
    fixed_tbody = fixed_soup.find('tbody')
    if not fixed_tbody:
        # Maybe the parsed result is the tbody itself
        if fixed_soup.name == 'tbody':
            fixed_tbody = fixed_soup
        else:
            # Look for tbody
            fixed_tbody = fixed_soup.find('tbody')
    if fixed_tbody:
        print(f"\nFixed tbody tag: {fixed_tbody.name}")
        print(f"Fixed tbody children count: {len(list(fixed_tbody.children))}")
        print("\nChildren of fixed tbody:")
        for i, child in enumerate(fixed_tbody.children):
            print(f"  Child {i}: {child}")
            if hasattr(child, 'name'):
                print(f"    name: {child.name}")
                if child.name == 'tr':
                    print(f"    This is a tr")
                else:
                    print(f"    Not a tr")
    else:
        print("Could not find tbody in fixed soup")
        # Print the fixed soup
        print(f"Fixed soup: {fixed_soup}")

if __name__ == "__main__":
    debug_tbody()