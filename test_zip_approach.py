#!/usr/bin/env python3
"""Test the new ZIP-based generation approach"""

from pathlib import Path
from excel_generator import generate_where_in
import sys

# Test with the latest version in current folder
input_file = Path("excel-files/Process logs bear/current/Process logs bear.xlsx")
output_file = Path("excel-files/Process logs bear/current/Process logs bear_v14_test.xlsx")

if not input_file.exists():
    print(f"❌ Input file not found: {input_file}")
    sys.exit(1)

print(f"📁 Input file: {input_file}")
print(f"📁 Output file: {output_file}")
print(f"📊 Input file size: {input_file.stat().st_size / 1024 / 1024:.2f} MB")

try:
    print("\n🔄 Generating with new ZIP-based approach...")
    generate_where_in(
        str(input_file),
        str(output_file),
        gen_name="Test ZIP",
        source_ref="Raw_records[Id]",
        has_header=True,
        where_col="Id",
        soql_base=None
    )
    
    if output_file.exists():
        output_size = output_file.stat().st_size / 1024 / 1024
        input_size = input_file.stat().st_size / 1024 / 1024
        print(f"\n✅ Generated successfully!")
        print(f"📊 Output file size: {output_size:.2f} MB")
        print(f"📊 Input file size:  {input_size:.2f} MB")
        print(f"📊 Size difference:  {abs(output_size - input_size):.2f} MB")
        
        if abs(output_size - input_size) > 0.5:
            print(f"⚠️  WARNING: Size difference > 0.5 MB (possible data loss)")
        else:
            print(f"✅ Size preserved (good sign!)")
    else:
        print(f"\n❌ Output file was not created")
        sys.exit(1)
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\n🧪 Test complete. Try opening {output_file} in Excel Desktop now.")
