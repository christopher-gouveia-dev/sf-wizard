# Test 01: Minimal Formula File vs Desktop Model

## Strategy
Test whether a minimal Excel file with a formula can be created that matches the structure of a desktop-created Excel file.

The issue may be that we're comparing generated files (which get deleted formulas) with the large online file (100K rows), when we should compare against a simple desktop-created file.

## Key Findings from Model Comparison
- **Desktop Empty File**: 670 bytes, minimal namespace, empty sheetData
- **Online File**: 11.6MB, 100K rows, extended namespaces (xr, xr2, xr3 for revision tracking)

## Test Goal
Create a minimal file following the desktop model structure:
1. No revision tracking namespaces (xr, xr2, xr3)
2. Simple formula in sheet1.xml
3. Desktop-like [Content_Types].xml
4. Minimal required elements

## What's Different
- ❌ Online has revision namespaces - desktop doesn't
- ❌ Online has 100K row dimension - generates repair message
- ✓ Both have basic formula support in <f> tags
- ✓ Both have styles.xml and theme1.xml

## Expected Outcome
If formula still deletes with desktop-like structure, issue is not about file size or revision tracking.

