import sys
import re
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))

from collectors.labs import LaboratoriesCollector

def count_tr(is_number="IS 2082:2018"):
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
    soup = BeautifulSoup(html_text, 'html.parser')
    table = soup.find('table', id='review_lab_list')
    if not table:
        print("Table not found")
        return
    tbody = table.find('tbody')
    if not tbody:
        print("No tbody")
        return
    print(f"Before fix: number of direct child tr elements: {len(tbody.find_all('tr', recursive=False))}")
    # Fix malformed </th> tags in tbody
    tbody_html = str(tbody)
    fixed_tbody_html = re.sub(r'</th>', '</td>', tbody_html)
    # Replace the tbody in the soup
    tbody.clear()
    fixed_tbody_soup = BeautifulSoup(fixed_tbody_html, 'html.parser')
    # The fixed_tbody_soup should contain the tbody element
    fixed_tbody = fixed_tbody_soup.find('tbody')
    if fixed_tbody is None:
        # Maybe the parsed result is the tbody itself
        if fixed_tbody_soup.name == 'tbody':
            fixed_tbody = fixed_tbody_soup
        else:
            fixed_tbody = fixed_tbody_soup.find('tbody')
    if fixed_tbody is None:
        print("Could not get fixed tbody")
        return
    # Replace tbody's children with fixed_tbody's children
    for element in list(tbody.children):  # copy list because we will modify
        tbody.extract(element)
    for element in fixed_tbody.children:
        tbody.append(element)
    print(f"After fix: number of direct child tr elements: {len(tbody.find_all('tr', recursive=False))}")
    # Let's also print the first tr's HTML
    first_tr = tbody.find('tr', recursive=False)
    if first_tr:
        print(f"First tr HTML (first 500 chars): {str(first_tr)[:500]}")
    else:
        print("No direct child tr found")

if __name__ == "__main__":
    count_tr()