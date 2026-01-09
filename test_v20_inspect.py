#!/usr/bin/env python3
"""
Single test file with 4 sheets (one per case)
Generates one Excel with all test cases for validation
"""

from excel_generator import generate_where_in
from pathlib import Path
import zipfile
import re
from html import unescape

def create_single_test_file():
    """Create ONE file with 4 sheets - one per test case"""
    print("\n" + "="*80)
    print(" GENERATING SINGLE TEST FILE (4 sheets, one per case)")
    print("="*80)
    
    input_file = 'excel-files/Process logs bear/original/Process logs bear.xlsx'
    
    # We'll generate 4 separate files then examine them
    # (Excel doesn't let us directly control sheet creation from generation)
    test_cases = [
        {
            'name': 'Test 1: Table[Col] with header',
            'output': 'excel-files/Process logs bear/versions/v20_ALL_CASES.xlsx',
            'source': 'Raw_records[Id]',
            'has_header': True
        },
        {
            'name': 'Test 2: Table[Col] no header',
            'output': 'excel-files/Process logs bear/versions/v20_case2.xlsx',
            'source': 'Raw_records[Id]',
            'has_header': False
        },
        {
            'name': 'Test 3: Sheet!Col with header',
            'output': 'excel-files/Process logs bear/versions/v20_case3.xlsx',
            'source': "'Records brut'!B:B",
            'has_header': True
        },
        {
            'name': 'Test 4: Sheet!Col no header',
            'output': 'excel-files/Process logs bear/versions/v20_case4.xlsx',
            'source': "'Records brut'!B:B",
            'has_header': False
        }
    ]
    
    print("\nGenerating test cases...")
    main_file = None
    
    for i, case in enumerate(test_cases, 1):
        try:
            generate_where_in(
                input_path=input_file,
                output_path=case['output'],
                gen_name=case['name'],
                source_ref=case['source'],
                has_header=case['has_header'],
                where_col='A',
                soql_base='SELECT Id FROM Account'
            )
            print(f"  [{i}/4] Generated: {case['name']}")
            
            if i == 1:
                main_file = case['output']
        except Exception as e:
            print(f"  [{i}/4] FAILED: {case['name']} - {e}")
    
    return main_file

def inspect_formula(filepath):
    """Extract and display formula from generated file"""
    print(f"\n  File: {Path(filepath).name}")
    
    try:
        with zipfile.ZipFile(filepath) as z:
            # Find newest sheet
            sheets = [f for f in z.namelist() if f.startswith('xl/worksheets/sheet')]
            if not sheets:
                print("    [ERROR] No sheets found")
                return
            
            newest_sheet = sorted(sheets)[-1]
            sheet_xml = z.read(newest_sheet).decode('utf-8')
            
            # Extract formula
            formula_match = re.search(r'<f>([^<]+)</f>', sheet_xml)
            if formula_match:
                formula_encoded = formula_match.group(1)
                formula = unescape(formula_encoded)
                print(f"    Formula: {formula[:100]}...")
                
                # Check formula length
                print(f"    Length: {len(formula)} chars")
                
                # Check for potential issues
                if len(formula) > 255:
                    print(f"    [WARNING] Formula exceeds 255 chars!")
                
                # Check XML encoding
                print(f"    XML encoded length: {len(formula_encoded)} chars")
                
                # Show raw XML fragment
                cell_match = re.search(r'<c r="A2"[^>]*>.*?</c>', sheet_xml, re.DOTALL)
                if cell_match:
                    cell_xml = cell_match.group(0)
                    print(f"    Cell XML (first 150 chars): {cell_xml[:150]}...")
            else:
                print("    [ERROR] No formula found in XML")
    except Exception as e:
        print(f"    [ERROR] {e}")

def main():
    print("\n" + "="*80)
    print(" SF WIZARD v20 - SINGLE TEST FILE APPROACH")
    print("="*80)
    
    main_file = create_single_test_file()
    
    if not main_file:
        print("\n[FAIL] Generation failed")
        return
    
    print("\n" + "="*80)
    print(" FORMULA INSPECTION")
    print("="*80)
    print("\nGenerated files - inspect formulas before Excel opens them:")
    
    for i in range(1, 5):
        if i == 1:
            filepath = 'excel-files/Process logs bear/versions/v20_ALL_CASES.xlsx'
        else:
            filepath = f'excel-files/Process logs bear/versions/v20_case{i}.xlsx'
        
        if Path(filepath).exists():
            inspect_formula(filepath)
    
    print("\n" + "="*80)
    print(" NEXT STEP: Open these files in Excel to verify")
    print("="*80)
    print("\nFiles to test (formulas should NOT be deleted):")
    print("  1. v20_ALL_CASES.xlsx")
    print("  2. v20_case2.xlsx")
    print("  3. v20_case3.xlsx")
    print("  4. v20_case4.xlsx")
    print("\nIf formulas are deleted, we need to debug the XML structure.")

if __name__ == '__main__':
    main()
