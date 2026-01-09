#!/usr/bin/env python3
"""
Generate ONE Excel with 4 sheets by chaining generations
Each output becomes the next input
"""

from excel_generator import generate_where_in
from pathlib import Path
from datetime import datetime
import re
import zipfile
from html import unescape

def run_test():
    """Chain 4 generations: output1 -> input2, output2 -> input3, etc."""
    
    tests_dir = Path("tests")
    tests_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_input = 'excel-files/Process logs bear/original/Process logs bear.xlsx'
    
    test_cases = [
        ('Case 1: Table[Col] with header', 'Raw_records[Id]', True),
        ('Case 2: Table[Col] no header', 'Raw_records[Id]', False),
        ('Case 3: Sheet!Col with header', "'Records brut'!B:B", True),
        ('Case 4: Sheet!Col no header', "'Records brut'!B:B", False),
    ]
    
    print("\n" + "="*80)
    print(" SF WIZARD v20 - ONE EXCEL WITH 4 SHEETS")
    print("="*80)
    print(f"\nChaining generations (each output → next input)\n")
    
    current_input = base_input
    final_output = None
    
    for i, (case_name, source, has_hdr) in enumerate(test_cases, 1):
        # Output is in tests/ with timestamp
        final_output = tests_dir / f"{timestamp}_v20_all_cases.xlsx"
        
        try:
            print(f"[{i}/4] {case_name}")
            generate_where_in(
                input_path=current_input,
                output_path=str(final_output),
                gen_name=case_name,
                source_ref=source,
                has_header=has_hdr,
                where_col='A',
                soql_base='SELECT Id FROM Account'
            )
            
            # Quick inspect
            with zipfile.ZipFile(final_output) as z:
                sheets = sorted([f for f in z.namelist() if f.startswith('xl/worksheets/sheet')])
                print(f"      Sheets now: {len(sheets)} ({sheets[-1] if sheets else 'none'})")
                
                # Show formula in newest sheet
                if sheets:
                    newest = sheets[-1]
                    content = z.read(newest).decode('utf-8')
                    formula_match = re.search(r'<f>([^<]+)</f>', content)
                    if formula_match:
                        formula = unescape(formula_match.group(1))
                        print(f"      Formula: {formula[:70]}...")
            
            # Next generation uses this output as input
            current_input = str(final_output)
            
        except Exception as e:
            print(f"      [FAIL] {e}")
            return None
    
    print("\n" + "="*80)
    print(" FILE READY")
    print("="*80)
    print(f"\nFile: {final_output}")
    print(f"  Contains 4 sheets (one per test case)")
    print(f"\nOpen in Excel and report if formulas are preserved")
    
    return final_output

if __name__ == '__main__':
    run_test()
