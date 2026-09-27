---
name: labs-parser-issue
description: Diagnosed the Laboratories parser issue in BIS26107 data pipeline
metadata:
  type: reference
---

The Laboratories collector in collectors/labs.py has incorrect column mapping. After HTML preprocessing, the actual column order in the parsed cell_texts array differs from what the code assumes, causing:

- Laboratory names to show Product values instead of Lab Name values
- Laboratory IDs to show Testing Charges values instead of Osl Code values

From test output analysis:
- All laboratory names show identical "Stationary storage type electric water heaters - Specification (Fifth Revision)" (Product field)
- Laboratory IDs show varying values including "-" , "NA", and Testing Charges-like text

This indicates the code is extracting:
- lab_name from wrong column (getting Product instead of Lab Name)
- lab_code from wrong column (getting Testing Charges instead of Osl Code)

The fix requires adjusting the column indices in lines 190-201 of collectors/labs.py to correctly map to the actual Lab Name and Osl Code columns in the cell_texts array.

Related to the LIMS laboratory search mechanism implementation for IS 2082:2018.