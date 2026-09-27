import sys
sys.path.insert(0, '/c/Users/NAME/Documents/Myprojects/BIS1')
from collectors.labs import LaboratoriesCollector
collector = LaboratoriesCollector()
html = collector._http_fetcher.fetch_raw_html('IS 2082:2018')  # Wait, we don't have that method.
# Actually we need to use the same as before.
# Let's just copy the fetch_raw_html function from our previous script.
import re
from bs4 import BeautifulSoup

def fetch_raw_html(is_number):
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
        raise RuntimeError(f"Failed to fetch HTML for {is_number}")
    return response.text

html = fetch_raw_html('IS 2082:2018')
print('Length:', len(html))
if 'review_lab_list' in html:
    print("String 'review_lab_list' found in raw HTML")
    # Show context
    import re
    matches = re.findall(r'.{0,100}review_lab_list.{0,100}', html)
    for m in matches[:5]:
        print(m)
else:
    print("String 'review_lab_list' NOT found in raw HTML")
    # Maybe it's in a different form? Check for 'review_lab' or something.
    if 'review_lab' in html:
        print("'review_lab' found")
    else:
        print("'review_lab' not found either")
# Save the HTML to a file for inspection
with open('debug_is2082_raw.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Raw HTML saved to debug_is2082_raw.html")