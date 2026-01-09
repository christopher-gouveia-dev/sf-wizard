# SF Wizard Formula Deletion Bug - Investigation Summary

## Problem Statement
All generated Excel files with WHERE IN formulas are having **all formulas deleted by Excel's repair process** when opened.

### Symptoms
- Excel repair dialog appears on file open
- Error message (French): "Enregistrements supprimés: Formule dans la partie /xl/worksheets/sheet{N}.xml"
- All 4 formulas deleted (one per sheet: sheet9, sheet10, sheet11, sheet12)
- Also: "Propriétés de la feuille de calcul dans la partie /xl/workbook.xml (Classeur)" - workbook properties corrupted

### Test File
- **Latest**: `tests/20251223_221148_v20_all_cases.xlsx`
- Contains 4 sheets with 1 formula each
- **Result**: STILL DELETES FORMULAS - Same error after fix attempts

---

## Solution Attempts

### Attempt 1: ZIP-based XML manipulation (SUCCESSFUL - no corruption)
- **Issue**: openpyxl's save() corrupts large Excel files
- **Solution**: Extract ZIP → edit XML as text → re-package without serialization
- **Result**: ✅ Files don't corrupt, ✅ Files open, but ❌ Formulas deleted

### Attempt 2: Formula structure fixes (ATTEMPTED - No improvement)
**Changes made to `excel_generator.py` lines 202-276:**

1. **Removed `=` prefix from formulas**
   - Before: `<f>=LET(col;'Sheet'!A:A;...)</f>`
   - After: `<f>LET(col;'Sheet'!A:A;...)</f>`
   - Reason: Excel XML formulas should NOT have `=` prefix

2. **Added array formula attributes**
   - Before: `<c r="A2" t="f"><f>{formula}</f><v></v></c>`
   - After: `<c r="A2" cm="1"><f t="array" aca="1" ref="A2" ca="1">{formula}</f><v></v></c>`
   - Reason: Matches working formulas from "SOQL auto" sheet with complex LET+RECHERCHE

3. **Formula pattern (French)**
   ```
   LET(col;'Sheet'!Col:Col;der;RECHERCHE(2;1/(col<>"");LIGNE(col));plage;INDEX(col;2):INDEX(col;der);plage)
   ```
   - Uses `RECHERCHE` instead of `LOOKUP` (French formula)
   - Auto-detects headers and finds last non-empty row

**Result**: ❌ FORMULAS STILL DELETED - Same Excel repair error persists

---

## Investigation: Comparison with Working Files

### Working File: `excel-files/Process logs bear/original/Process logs bear.xlsx`
- Sheet: "SOQL auto" (sheet6.xml) - **HAS COMPLEX FORMULAS THAT WORK**
- Sheet: "SOQL" (sheet7.xml) - **HAS SIMPLE FORMULAS THAT WORK**

### Key Findings from XML Inspection:

#### Formula Cells in WORKING sheet (sheet7.xml):
```xml
<!-- Simple array formula -->
<c r="C2" cm="1"><f t="array" aca="1" ref="C2" ca="1">LOOKUP(5,1/(B:B<>""),ROW(B:B))</f><v>181</v></c>

<!-- Array formula with string result -->
<c r="A5" t="str" cm="1"><f t="array" aca="1" ref="A5" ca="1">IFERROR(...)</f><v>❌ Impossible</v></c>

<!-- Simple formula (no array marker) -->
<c r="D2"><f ca="1">LEN(B5)</f><v>11984</v></c>
```

#### Generated Formula (sheet9.xml):
```xml
<c r="A2" cm="1"><f t="array" aca="1" ref="A2" ca="1">LET(col;'Records brut'!B:B;...)</f><v></v></c>
```

---

## Potential Root Causes (Not Yet Resolved)

1. **`<v>` element is empty** - Working formulas have calculated values
   - Generated: `<v></v>` (empty)
   - Working: `<v>181</v>` or `<v>❌ Impossible</v>`
   - **Hypothesis**: Empty value may signal "corrupted" to Excel

2. **Missing sheet-level metadata**
   - Generated sheets cloned from sheet1 (minimal template)
   - Working sheets may have additional attributes or structure
   - **Need**: Full XML comparison between working sheet and generated sheet

3. **Workbook registration issue**
   - Sheets registered in: `xl/workbook.xml`, `xl/workbook.xml.rels`, `[Content_Types].xml`
   - Error mentions: "Propriétés de la feuille de calcul dans la partie /xl/workbook.xml"
   - **Hypothesis**: New sheet registration may be incomplete or malformed

---

## Code Changes Made

### File: `excel_generator.py`

**Lines 202, 213, 226, 233**: Removed `=` prefix
```python
# OLD: formula = f"=LET(col;'{sheet_name}'!{target_col_str}:..."
# NEW: formula = f"LET(col;'{sheet_name}'!{target_col_str}:..."
```

**Lines 262-276**: Updated cell structure
```python
# OLD:
# <c r="A2" t="f">
#   <f>{escape(formula)}</f>
#   <v></v>
# </c>

# NEW:
# <c r="A2" cm="1"><f t="array" aca="1" ref="A2" ca="1">{escape(formula)}</f><v></v></c>
```

---

## Next Investigation Steps

### CRITICAL: Compare Full Sheet XML Structure
1. Extract working sheet (sheet7.xml) from original file
2. Extract generated sheet (sheet9.xml) from test file
3. Perform unified diff to identify ALL differences
4. Focus on:
   - Root `<worksheet>` attributes
   - `<dimension>` element (determines valid cell range)
   - `<sheetPr>` (sheet properties)
   - `<cols>` (column width definitions)
   - `<sheetData>` structure beyond just the formula cell
   - Any other top-level elements

### Potential Fixes to Test
- Fill `<v>` with placeholder value (e.g., `<v>#PENDING</v>`)
- Add `t="str"` or `t="n"` to formula cell
- Copy ALL sheet-level XML from original sheet7 (not just sheetData)
- Verify sheet registration in workbook.xml is correct

---

## File Locations

### Working Directory
```
c:\Users\Predator Orion 3000\Documents\Dev\Analyse données SF\sf-wizard\v2-work
```

### Key Files
- **Generator**: `excel_generator.py` (lines 147-276 have formula building & cell structure)
- **Test Script**: `test_v20_one_file.py` (chains 4 generations into 1 Excel)
- **Original Data**: `excel-files/Process logs bear/original/Process logs bear.xlsx` (reference)
- **Test Output**: `tests/20251223_221148_v20_all_cases.xlsx` (latest - FORMULAS DELETED)

### To Inspect Generated Files
```python
import zipfile
with zipfile.ZipFile('tests/20251223_221148_v20_all_cases.xlsx') as z:
    sheet9 = z.read('xl/worksheets/sheet9.xml').decode('utf-8')
    print(sheet9)
```

---

## Testing Workflow

```bash
cd "c:\Users\Predator Orion 3000\Documents\Dev\Analyse données SF\sf-wizard\v2-work"

# Run test (generates new Excel)
python test_v20_one_file.py

# Open in Excel
start tests/[latest_timestamp]_v20_all_cases.xlsx

# Check repair dialog or formula presence
```

---

## Success Criteria

- ✅ No repair dialog (or repair without formula deletions)
- ✅ Formulas visible in cells
- ✅ Formulas calculate correctly

