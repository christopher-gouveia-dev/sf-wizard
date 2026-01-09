#!/usr/bin/env python3
"""
Generate ONE Excel with 4 sheets (one per test case)
Save to timestamped folder in tests/
Debug formula deletion
"""

from pathlib import Path
from datetime import datetime
import zipfile
import shutil
import re
from html import unescape
import xml.etree.ElementTree as ET

def create_timestamped_test():
    """Create timestamped test file and generate single file with 4 sheets"""
    
    # Create tests folder
    tests_dir = Path("tests")
    tests_dir.mkdir(exist_ok=True)
    
    # Timestamped file (directly in tests/, not in subfolder)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = tests_dir / f'v20_test_{timestamp}.xlsx'
    print(f"\nOutput file: {output_file}")
    
    # Generate base file (will clone it for each sheet)
    input_file = 'excel-files/Process logs bear/original/Process logs bear.xlsx'
    output_file = tests_dir / f'v20_test_{timestamp}.xlsx'
    
    from excel_generator import generate_where_in
    
    test_cases = [
        {
            'gen_name': 'Case 1 - Table[Col] with header',
            'source': 'Raw_records[Id]',
            'has_header': True
        },
        {
            'gen_name': 'Case 2 - Table[Col] no header',
            'source': 'Raw_records[Id]',
            'has_header': False
        },
        {
            'gen_name': 'Case 3 - Sheet!Col with header',
            'source': "'Records brut'!B:B",
            'has_header': True
        },
        {
            'gen_name': 'Case 4 - Sheet!Col no header',
            'source': "'Records brut'!B:B",
            'has_header': False
        }
    ]
    
    print("\n" + "="*80)
    print(" GENERATING ONE EXCEL WITH 4 SHEETS")
    print("="*80)
    
    # Generate first file as base
    temp_files = []
    for i, case in enumerate(test_cases, 1):
        temp_file = tests_dir / f"temp_case{i}_{timestamp}.xlsx"
        try:
            generate_where_in(
                input_path=input_file,
                output_path=str(temp_file),
                gen_name=case['gen_name'],
                source_ref=case['source'],
                has_header=case['has_header'],
                where_col='A',
                soql_base='SELECT Id FROM Account'
            )
            temp_files.append((i, temp_file, case['gen_name']))
            print(f"  [{i}/4] Generated: {case['gen_name']}")
        except Exception as e:
            print(f"  [{i}/4] FAILED: {e}")
    
    if not temp_files:
        print("\n[FAIL] No files generated")
        return None, test_dir
    
    # Now merge all sheets into one file
    print("\n" + "="*80)
    print(" MERGING INTO SINGLE FILE")
    print("="*80)
    
    # Start with first file
    first_case_num, first_temp, first_name = temp_files[0]
    shutil.copy(first_temp, output_file)
    print(f"  Base file: {first_name}")
    
    # Extract all sheets and metadata from all files
    all_sheets = {}  # sheet_num -> content
    wb_rels = {}  # rId -> target
    
    for case_num, temp_file, case_name in temp_files:
        with zipfile.ZipFile(temp_file, 'r') as temp_zip:
            sheets = [f for f in temp_zip.namelist() if f.startswith('xl/worksheets/sheet')]
            if sheets:
                newest = sorted(sheets)[-1]
                sheet_num = int(re.search(r'sheet(\d+)', newest).group(1))
                all_sheets[sheet_num] = temp_zip.read(newest)
                
                if case_num > 1:
                    print(f"  Extracted: {case_name} from {newest}")
    
    # Rebuild the output file with all sheets
    with zipfile.ZipFile(output_file, 'r') as z:
        base_files = {name: z.read(name) for name in z.namelist()}
    
    # Prepare new file content
    new_files = dict(base_files)
    
    # Add new sheets (10, 11, 12)
    for new_num, sheet_content in sorted(all_sheets.items()):
        if new_num > 9:  # Don't overwrite originals
            continue
        # The first new sheet will be 10
        sheet_10_num = 9
    
    # Add sheets 10, 11, 12 from our test cases
    for idx, (sheet_num, content) in enumerate(sorted(all_sheets.items())[1:], start=10):
        new_files[f'xl/worksheets/sheet{idx}.xml'] = content
    
    # Rewrite entire ZIP cleanly
    temp_output = output_file.with_suffix('.tmp')
    with zipfile.ZipFile(temp_output, 'w', zipfile.ZIP_DEFLATED) as z_new:
        for fname, content in sorted(new_files.items()):
            z_new.writestr(fname, content)
    
    # Replace original
    temp_output.replace(output_file)
    print(f"  Merged 4 sheets into single file")
    
    print(f"\nMerged file: {output_file}")
    return output_file

def inspect_and_debug(filepath):
    """Inspect XML structure and look for issues"""
    print("\n" + "="*80)
    print(" XML DEBUGGING")
    print("="*80)
    
    with zipfile.ZipFile(filepath) as z:
        sheets = sorted([f for f in z.namelist() if f.startswith('xl/worksheets/sheet')])
        
        for sheet_file in sheets[-4:]:  # Last 4 sheets (our new ones)
            print(f"\n{sheet_file}:")
            sheet_xml = z.read(sheet_file).decode('utf-8')
            
            # Find formula cell
            cell_match = re.search(r'<c r="A2"[^>]*>.*?</c>', sheet_xml, re.DOTALL)
            if cell_match:
                cell_xml = cell_match.group(0)
                print(f"  Cell XML:\n    {cell_xml[:200]}...")
                
                # Check structure
                has_formula = '<f>' in cell_xml
                has_value = '<v>' in cell_xml
                print(f"  Has <f>: {has_formula}")
                print(f"  Has <v>: {has_value}")
                
                # Extract formula
                formula_match = re.search(r'<f>([^<]+)</f>', cell_xml)
                if formula_match:
                    formula = unescape(formula_match.group(1))
                    print(f"  Formula: {formula[:100]}...")
                else:
                    print(f"  ERROR: No formula found!")
            else:
                print(f"  ERROR: Cell A2 not found!")

def main():
    print("\n" + "="*80)
    print(" SF WIZARD v20 - SINGLE FILE TEST (TIMESTAMPED)")
    print("="*80)
    
    output_file = create_timestamped_test()
    
    if not output_file:
        return
    
    inspect_and_debug(output_file)
    
    print("\n" + "="*80)
    print(" TEST FILE READY")
    print("="*80)
    print(f"\nFile: {output_file}")
    print("\nContains 4 sheets (one per test case):")
    print("  - Case 1: Table[Col] with header")
    print("  - Case 2: Table[Col] no header")
    print("  - Case 3: Sheet!Col with header")
    print("  - Case 4: Sheet!Col no header")
    print(f"\nOpen in Excel and report if formulas are deleted or preserved")

if __name__ == '__main__':
    main()
