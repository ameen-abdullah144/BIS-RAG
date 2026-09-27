from bs4 import BeautifulSoup
snippet = '''<table class="table table-bordered customTable" id="dataTable" width="100%" cellspacing="0" id="review_lab_list">
  <thead>
    <tr>
      <th scope="col" width="40">S.No.</th>
      <th scope="col">Lab Name</th>
      <th scope="col">Osl Code</th>
      <th scope="col">Indian Standard No.</th>
      <th scope="col">Product</th>
      <th scope="col">Grade / Type / Size / Designation etc.</th>
      <th scope="col">Testing Charges (Excl. Of Taxes)</th>
      <th scope="col">Validity Date</th>
      <th scope="col">Remark</th>
    </tr>
  </thead>
  <tbody>
    <tr id="tr_45786">
      <td>1</td>
      <td>Samridhi Test House Pvt. Ltd.</th>
      <td>8184706</th>
      <td>IS 2082 (2018)</td>
      <td>Stationary storage type electric water heaters - Specification (Fifth Revision)</td>
      <td>All Grade / Type / Size / Designation</td>
      <td><!-- <td>


  </tbody>
</table>'''

soup = BeautifulSoup(snippet, 'lxml')
print("Parsed with lxml:")
table = soup.find('table', id='review_lab_list')
print("Table found:", table is not None)
if table:
    print("Table id:", table.get('id'))
    # Find tbody
    tbody = table.find('tbody')
    if tbody:
        rows = tbody.find_all('tr')
        print("Number of rows in tbody:", len(rows))
        if rows:
            first_row = rows[0]
            cells = first_row.find_all(['td', 'th'])
            print("Number of cells in first row:", len(cells))
            for i, cell in enumerate(cells):
                print(f"  Cell {i}: name={cell.name}, text={cell.get_text(strip=True)}")

soup2 = BeautifulSoup(snippet, 'html.parser')
print("\nParsed with html.parser:")
table2 = soup2.find('table', id='review_lab_list')
print("Table found:", table2 is not None)
if table2:
    print("Table id:", table2.get('id'))
    tbody2 = table2.find('tbody')
    if tbody2:
        rows2 = tbody2.find_all('tr')
        print("Number of rows in tbody:", len(rows2))
        if rows2:
            first_row2 = rows2[0]
            cells2 = first_row2.find_all(['td', 'th'])
            print("Number of cells in first row:", len(cells2))
            for i, cell in enumerate(cells2):
                print(f"  Cell {i}: name={cell.name}, text={cell.get_text(strip=True)}")