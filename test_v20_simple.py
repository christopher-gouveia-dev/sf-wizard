#!/usr/bin/env python3
"""
Simple test: Generate 4 timestamped Excel files (one per case) directly in tests/
No merging complexity
"""

from excel_generator import generate_where_in
from pathlib import Path
from datetime import datetime
import re
import zipfile
from html import unescape

def run_tests():
    """Generate 4 test files directly in tests/ with timestamp"""
    
    tests_dir = Path("tests")
    tests_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    input_file = 'excel-files/Process logs bear/original/Process logs bear.xlsx'
    
    test_cases = [
        ('Case1_Table_Header', 'Raw_records[Id]', True),
        ('Case2_Table_NoHeader', 'Raw_records[Id]', False),
        ('Case3_Sheet_Header', "'Records brut'!B:B", True),
        ('Case4_Sheet_NoHeader', "'Records brut'!B:B", False),
    ]
    
    print("\n" + "="*80)
    print(" SF WIZARD v20 - TEST FILES (4 separate excels)")
    print("="*80)
    print(f"\nTimestamp: {timestamp}")
    print(f"Output dir: {tests_dir}\n")
    
    generated_files = []
    
    for case_name, source, has_hdr in test_cases:
        output = tests_dir / f"{timestamp}_{case_name}.xlsx"
        try:
            generate_where_in(
                input_path=input_file,
                output_path=str(output),
                gen_name=case_name,
                source_ref=source,
                has_header=has_hdr,
                where_col='A',
                soql_base='SELECT Id FROM Account'
            )
            generated_files.append((case_name, output))
            print(f"[OK] {case_name} -> {output.name}")
            
            # Quick inspect
            with zipfile.ZipFile(output) as z:
                sheets = sorted([f for f in z.namelist() if f.startswith('xl/worksheets/sheet')])
                if sheets:
                    newest = sheets[-1]
                    content = z.read(newest).decode('utf-8')
                    if '<f>' in content:
                        formula_match = re.search(r'<f>([^<]+)</f>', content)
                        if formula_match:
                            formula = unescape(formula_match.group(1))
                            print(f"     Formula: {formula[:80]}...")
        except Exception as e:
            print(f"[FAIL] {case_name}: {e}")
    
    print("\n" + "="*80)
    print(" FILES READY")
    print("="*80)
    print(f"\nOpen in Excel: tests/{timestamp}_*.xlsx")
    print(f"\nReport:")
    print("  - Do files open without repair dialog?")
    print("  - Are all 4 formulas preserved?")

if __name__ == '__main__':
    run_tests()
