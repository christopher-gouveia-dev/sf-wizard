#!/usr/bin/env python3
"""
Compare generated test file with reference models
"""
import sys
from pathlib import Path
import zipfile
import difflib

def extract_and_compare(test_xlsx, output_dir):
    """Extract test file and compare with models"""
    test_dir = Path(output_dir)
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract test file XML
    xml_dir = test_dir / "xml"
    xml_dir.mkdir(exist_ok=True)
    
    with zipfile.ZipFile(test_xlsx) as z:
        for name in z.namelist():
            if name.endswith('.xml'):
                content = z.read(name).decode('utf-8')
                xml_path = xml_dir / name
                xml_path.parent.mkdir(parents=True, exist_ok=True)
                xml_path.write_text(content, encoding='utf-8')
    
    # Compare with models
    models_base = Path(__file__).parent / "00_REFERENCE_MODELS"
    
    comparison = test_dir / "COMPARISON.txt"
    with open(comparison, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write(f"TEST: {Path(test_xlsx).name}\n")
        f.write("="*80 + "\n\n")
        
        # Compare key files
        key_files = [
            "[Content_Types].xml",
            "xl/workbook.xml",
            "xl/worksheets/sheet1.xml",
            "xl/worksheets/sheet2.xml",  # Will be generated sheet
        ]
        
        for fpath in key_files:
            f.write(f"\n{'='*80}\n")
            f.write(f"FILE: {fpath}\n")
            f.write(f"{'='*80}\n")
            
            test_file = xml_dir / fpath
            if not test_file.exists():
                f.write(f"  ✗ NOT IN TEST FILE\n")
                continue
            
            f.write(f"  ✓ Found ({test_file.stat().st_size} bytes)\n\n")
            
            # Show content
            content = test_file.read_text(encoding='utf-8')
            f.write("CONTENT (first 1000 chars):\n")
            f.write("-"*80 + "\n")
            f.write(content[:1000])
            f.write("\n...\n\n")
            
            # Compare with desktop model
            desktop_file = models_base / "simple_desktop" / "xml" / fpath
            if desktop_file.exists():
                f.write("COMPARISON WITH simple_desktop:\n")
                f.write("-"*80 + "\n")
                
                test_lines = content.splitlines()
                desktop_lines = desktop_file.read_text(encoding='utf-8').splitlines()
                
                diff = list(difflib.unified_diff(
                    desktop_lines, test_lines,
                    fromfile='simple_desktop',
                    tofile='test',
                    lineterm='',
                    n=2
                ))
                
                if diff:
                    f.write("DIFFERENCES FOUND:\n")
                    for line in diff[:50]:  # First 50 diff lines
                        f.write(line + "\n")
                    if len(diff) > 50:
                        f.write(f"\n... and {len(diff)-50} more differences\n")
                else:
                    f.write("✓ IDENTICAL\n")
    
    print(f"✓ Comparison saved to: {comparison}")
    return comparison

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compare_test.py <test_xlsx_path> <output_dir>")
        sys.exit(1)
    
    test_xlsx = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else Path(test_xlsx).stem + "_analysis"
    
    extract_and_compare(test_xlsx, output_dir)
