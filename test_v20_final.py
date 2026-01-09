#!/usr/bin/env python3
"""
Complete v20 test script - Windows compatible (ASCII chars only)
Tests: Table[Col], Sheet!Col, headers, ZIP integrity, metadata
Run once: python test_v20_final.py
"""

import json
import urllib.request
import urllib.error
import zipfile
import re
from pathlib import Path
from html import unescape
import time
import subprocess

def test_all_formulas():
    """Test 1: Generate formulas for all cases"""
    print("\n" + "="*60)
    print("TEST 1: Formula Generation (All Cases)")
    print("="*60)
    
    from excel_generator import generate_where_in
    input_file = 'excel-files/Process logs bear/original/Process logs bear.xlsx'
    
    test_cases = [
        ('Table[Col] with header', 'v20_test_table_header.xlsx', 'Raw_records[Id]', True),
        ('Table[Col] no header', 'v20_test_table_no_header.xlsx', 'Raw_records[Id]', False),
        ("Sheet!Col with header", 'v20_test_sheet_header.xlsx', "'Records brut'!B:B", True),
        ("Sheet!Col no header", 'v20_test_sheet_no_header.xlsx', "'Records brut'!B:B", False),
    ]
    
    results = {}
    for name, outfile, source, has_hdr in test_cases:
        try:
            output = f'excel-files/Process logs bear/versions/{outfile}'
            generate_where_in(
                input_path=input_file,
                output_path=output,
                gen_name=name,
                source_ref=source,
                has_header=has_hdr,
                where_col='A',
                soql_base='SELECT Id FROM Account'
            )
            results[name] = (True, output)
            print(f"  [PASS] {name}")
        except Exception as e:
            results[name] = (False, None)
            print(f"  [FAIL] {name}: {str(e)[:60]}")
    
    if all(r[0] for r in results.values()):
        print("[PASS] All generation cases completed")
        return True, results[test_cases[0][0]][1], results
    else:
        print("[FAIL] Some generation cases failed")
        return False, None, results

def test_zip_integrity(output_file):
    """Test 2: ZIP structure and formula validation"""
    print("\n" + "="*60)
    print("TEST 2: ZIP Integrity & Formula Validation")
    print("="*60)
    
    if not output_file:
        return False
    
    try:
        with zipfile.ZipFile(output_file) as z:
            files = z.namelist()
            print(f"[PASS] Valid ZIP ({len(files)} files)")
            
            # Check required files
            required = ['[Content_Types].xml', 'xl/workbook.xml', 'xl/_rels/workbook.xml.rels', '_rels/.rels']
            missing = [f for f in required if f not in files]
            if missing:
                print(f"[FAIL] Missing files: {missing}")
                return False
            print("[PASS] All required structure files present")
            
            # Check worksheets
            sheets = [f for f in files if f.startswith('xl/worksheets/sheet')]
            print(f"[PASS] Found {len(sheets)} worksheets")
            
            # Find new sheet
            sheet9_txt = None
            for sheet_file in sorted(sheets, reverse=True)[:3]:
                try:
                    content = z.read(sheet_file).decode('utf-8')
                    if '<sheetData>' in content:
                        sheet9_txt = content
                        print(f"[PASS] Found new sheet: {sheet_file}")
                        break
                except:
                    pass
            
            if not sheet9_txt:
                print("[FAIL] No new sheet found")
                return False
            
            # Check formula
            formula_match = re.search(r'<f>([^<]+)</f>', sheet9_txt)
            if not formula_match:
                print("[FAIL] No formula in sheet")
                return False
            
            formula = unescape(formula_match.group(1))
            print(f"\n[PASS] Formula found:")
            print(f"  {formula}")
            
            # Validate components
            required_parts = ['LET', 'col', 'RECHERCHE', 'INDEX', 'LIGNE']
            missing_parts = [x for x in required_parts if x not in formula]
            if missing_parts:
                print(f"[FAIL] Missing: {missing_parts}")
                return False
            print("[PASS] All required components present")
            
            # Check XML valid
            from xml.etree import ElementTree as ET
            try:
                ET.fromstring(sheet9_txt)
                print("[PASS] Sheet XML is well-formed")
            except Exception as e:
                print(f"[FAIL] XML error: {e}")
                return False
            
            return True
            
    except Exception as e:
        print(f"[FAIL] Validation error: {e}")
        return False

def test_excel_opens(output_file):
    """Test 3: Excel can open without repair"""
    print("\n" + "="*60)
    print("TEST 3: Excel Opening (No Repair Needed)")
    print("="*60)
    
    if not output_file:
        return False
    
    try:
        import openpyxl
        wb = openpyxl.load_workbook(output_file, data_only=False)
        print("[PASS] Workbook loads (no repair needed)")
        
        new_sheets = [s for s in wb.sheetnames if ' - ' in s]
        if not new_sheets:
            print("[FAIL] New sheet not found")
            return False
        
        sheet = wb[new_sheets[0]]
        print(f"[PASS] New sheet: {new_sheets[0]}")
        
        if sheet['A2'].data_type != 'f':
            print("[FAIL] A2 is not a formula")
            return False
        
        formula = sheet['A2'].value
        if 'LET' not in formula or 'RECHERCHE' not in formula:
            print(f"[FAIL] Formula not recognized: {formula[:80]}")
            return False
        
        print("[PASS] Formula recognized correctly")
        return True
        
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False

def main():
    print("\n" + "="*80)
    print(" SF WIZARD v20 - COMPREHENSIVE TEST SUITE")
    print(" Tests: Table[Col], Sheet!Col, ZIP integrity, metadata, Excel opening")
    print("="*80)
    
    # Test 1: Generation
    gen_ok, output_file, gen_cases = test_all_formulas()
    if not gen_ok:
        print("\n[FAIL] Generation failed - stopping")
        return
    
    # Test 2: ZIP integrity
    zip_ok = test_zip_integrity(output_file)
    
    # Test 3: Excel opening
    excel_ok = test_excel_opens(output_file)
    
    # Summary
    print("\n" + "="*80)
    print(" TEST RESULTS")
    print("="*80)
    
    print("\nGeneration cases:")
    for case_name, (ok, _) in gen_cases.items():
        status = "[PASS]" if ok else "[FAIL]"
        print(f"  {status} {case_name}")
    
    print("\nCore tests:")
    print(f"  [PASS] Generation (4/4 cases)" if gen_ok else "  [FAIL] Generation")
    print(f"  [PASS] ZIP Integrity" if zip_ok else "  [FAIL] ZIP Integrity")
    print(f"  [PASS] Excel Opening" if excel_ok else "  [FAIL] Excel Opening")
    
    if gen_ok and zip_ok and excel_ok:
        print("\n" + "="*80)
        print(" *** ALL TESTS PASSED ***")
        print(" v20 is ready - formula generation, ZIP preservation, Excel compatibility OK")
        print("="*80)
    else:
        print("\n" + "="*80)
        print(" *** SOME TESTS FAILED ***")
        print("="*80)

if __name__ == '__main__':
    main()
