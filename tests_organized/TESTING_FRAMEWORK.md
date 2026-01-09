# Formula Deletion Bug - Testing Framework

## Problem Statement
Generated Excel files have formulas deleted when opened, with Excel repair dialog showing:
"Enregistrements supprimés: Formule dans la partie /xl/worksheets/sheet{N}.xml"

## Reference Models

### 1. **original_online** 
- Source: `excel-files/Process logs bear/original/Process logs bear.xlsx`
- 8 worksheets with complex formulas
- **Working**: Formulas preserved when opened online
- **XML Note**: Contains calcChain.xml, metadata.xml, tables, themes

### 2. **current_online**
- Source: `excel-files/Process logs bear/current/Process logs bear.xlsx`
- Same as original (reference copy)
- **Working**: Formulas preserved when opened online

### 3. **simple_desktop**
- Source: Simple Excel file created on Windows desktop
- Only sheet1.xml with basic data
- **Reference**: Minimal valid Excel structure
- **Purpose**: Compare with minimal generated files

## Test Structure

Each test gets a folder with:
```
TEST_NAME/
  ├── README.txt          # Explanation of test strategy
  ├── test_case.xlsx      # Generated file to test
  ├── test_case_XML/      # Extracted XML from test file
  └── RESULTS.txt         # Open/repair results
```

## Key XML Elements to Compare

1. **Worksheet Structure** (`xl/worksheets/sheet1.xml`)
   - `<dimension>` - range definition
   - `<cols>` - column widths
   - `<f>` - formula element
   - Formula content and escaping

2. **Workbook Metadata** (`xl/workbook.xml`)
   - Sheet definitions
   - documentId (version tracking)
   - calcId

3. **Content Types** (`[Content_Types].xml`)
   - Worksheet MIME type registration

4. **Relationships** (`xl/_rels/workbook.xml.rels`, `xl/worksheets/_rels/sheet1.xml.rels`)
   - Sheet registration
   - External references

## Testing Process

1. Generate test file
2. Extract XML to `test_case_XML/`
3. Open file in Excel
4. Record repair dialog or successful open
5. Compare XML with reference models
6. Document findings in RESULTS.txt

## Current Hypothesis

❌ **Escaping not the issue** - Applied `html.escape()` but formulas still deleted

❌ **Minimal structure fails too** - Even blank minimal files get formula deletion

❌ **Missing columns NOT the fix** - Added `<cols>` but issue persists

🔍 **Next: Compare full structure with working models to find what's different**

