from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import tempfile
from html import escape


_FUNC_MAP = {
    # English to French function name mapping (common functions used)
    "FILTER": "FILTRE",
    "UNIQUE": "UNIQUE",
    "LET": "LET",
    "LOOKUP": "RECHERCHE",
    "INDEX": "INDEX",
    "ROW": "LIGNE",
    "ROWS": "LIGNES",
    "MIN": "MIN",
    "MAX": "MAX",
    "IF": "SI",
    "TRIM": "SUPPRESPACE",
    "TEXTJOIN": "JOINDRE.TEXTE",
    "ROUNDUP": "ARRONDI.SUP",
    "MAP": "MAP",
    "SEQUENCE": "SEQUENCE",
    "LAMBDA": "LAMBDA",
    "LEN": "NBCAR",
    "TRIM": "SUPPRESPACE",
}


def _translate_formula_to_french(formula: str) -> str:
    """Translate English Excel function names to French and add line breaks.

    Replacements are only applied outside quoted strings. Commas are
    converted to semicolons and a newline is inserted after the separator
    for readability in the Excel formula bar.
    """
    out = []
    i = 0
    s = formula
    L = len(s)
    in_quote = False

    while i < L:
        c = s[i]
        if c == '"':
            # toggle quote mode and copy verbatim until next quote
            out.append(c)
            i += 1
            in_quote = not in_quote
            continue

        if not in_quote:
            # function name detection: letters, digits or underscore then '('
            m = re.match(r"([A-Za-z_][A-Za-z0-9_.]*)\s*\(", s[i:])
            if m:
                name = m.group(1).upper()
                mapped = _FUNC_MAP.get(name, name)
                out.append(mapped)
                out.append('(')
                i += m.end()
                continue

            # boolean constants
            if s[i : i + 4].upper() == 'TRUE' and (i + 4 == L or not s[i + 4].isalpha()):
                out.append('VRAI')
                i += 4
                continue
            if s[i : i + 5].upper() == 'FALSE' and (i + 5 == L or not s[i + 5].isalpha()):
                out.append('FAUX')
                i += 5
                continue

            # comma separators -> semicolon (no newline)
            if c == ',':
                out.append(';')
                i += 1
                continue

        # default copy
        out.append(c)
        i += 1

    return ''.join(out)

def next_n(workbook):
    n = 0
    for ws in workbook.worksheets:
        m = re.match(r"(\d+)\s-\s", ws.title)
        if m:
            n = max(n, int(m.group(1)))
    return n + 1


def generate_where_in(
    input_path,
    output_path,
    gen_name,
    source_ref,
    has_header,
    where_col,
    soql_base,
):
    """
    Generate WHERE IN sheet using ZIP manipulation instead of openpyxl save.
    This preserves Excel Online metadata and internal structures.
    """
    # Step 1: Create a temporary directory for extraction
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        extract_dir = tmpdir / "extracted"
        extract_dir.mkdir()
        
        # Step 2: Extract input file as ZIP
        with zipfile.ZipFile(input_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Step 3: Parse workbook.xml directly to get next sheet number
        wb_xml_path = extract_dir / "xl" / "workbook.xml"
        wb_tree = ET.parse(wb_xml_path)
        wb_root = wb_tree.getroot()
        
        # Find all sheet elements and get max ID
        sheets = wb_root.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheets")
        max_sheet_id = 0
        max_sheet_num = 0
        
        for sheet_elem in sheets.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet"):
            sheet_id = int(sheet_elem.get('sheetId', 0))
            sheet_name = sheet_elem.get('name', '')
            # Extract number from name like "11 - Logs"
            match = re.match(r"(\d+)\s-\s", sheet_name)
            if match:
                num = int(match.group(1))
                max_sheet_num = max(max_sheet_num, num)
            max_sheet_id = max(max_sheet_id, sheet_id)
        
        n = max_sheet_num + 1
        ds_name = f"{n} - {gen_name}"
        # Sanitize sheet name: remove invalid Excel sheet characters: [ ] : * ? / \
        ds_name = re.sub(r'[\[\]:*?/\\]', '', ds_name)
        new_sheet_id = max_sheet_id + 1
        
        # Step 4: Build the formula using French syntax (LET+RECHERCHE pattern)
        # Formula detects headers and finds last non-empty row automatically
        
        if "[" in source_ref and source_ref.endswith("]"):
            # Table[Col] format - resolve to sheet!col via table metadata
            table_name, col_name = source_ref.split("[")
            col_name = col_name[:-1]  # remove ]
            
            # Find table file and extract sheet+column
            table_file = None
            for tbl_path in (extract_dir / 'xl' / 'tables').glob('*.xml'):
                tbl_txt = tbl_path.read_text(encoding='utf-8')
                if f'name="{table_name}"' in tbl_txt or f'displayName="{table_name}"' in tbl_txt:
                    table_file = tbl_path
                    break
            
            if table_file is None:
                # No table found, use structured ref as-is (will likely fail, but fallback)
                formula = f"UNIQUE({source_ref})"
            else:
                # Extract table metadata: ref range and columns
                table_txt = table_file.read_text(encoding='utf-8')
                ref_match = re.search(r'ref="([A-Z]+)(\d+):([A-Z]+)(\d+)"', table_txt)
                if ref_match:
                    start_col_str = ref_match.group(1)
                    # Parse columns to find index of col_name
                    col_names = re.findall(r'<tableColumn[^>]*name="([^"]+)"', table_txt)
                    if col_name in col_names:
                        col_idx = col_names.index(col_name)
                        # Convert start_col (A, B, etc) to number
                        def col_letter_to_num(s):
                            n = 0
                            for c in s:
                                n = n * 26 + (ord(c) - ord('A') + 1)
                            return n
                        def col_num_to_letter(n):
                            s = ''
                            while n > 0:
                                n, r = divmod(n - 1, 26)
                                s = chr(ord('A') + r) + s
                            return s
                        target_col_num = col_letter_to_num(start_col_str) + col_idx
                        target_col_str = col_num_to_letter(target_col_num)
                        
                        # Find sheet name: locate worksheet containing this table
                        sheet_name = None
                        for ws_path in (extract_dir / 'xl' / 'worksheets').glob('*.xml'):
                            # Check if this worksheet has a relationship to our table
                            ws_rels_path = ws_path.parent / '_rels' / f'{ws_path.name}.rels'
                            if ws_rels_path.exists():
                                ws_rels_txt = ws_rels_path.read_text(encoding='utf-8')
                                if 'tables/table' in ws_rels_txt and table_file.name in ws_rels_txt:
                                    # Found the worksheet with this table
                                    # Now map it to sheet name via workbook.xml.rels and workbook.xml
                                    rels_txt = (extract_dir / 'xl' / '_rels' / 'workbook.xml.rels').read_text(encoding='utf-8')
                                    target_path = f"worksheets/{ws_path.name}"
                                    rid_match = re.search(rf'Id="(rId\d+)"[^>]*Target="{re.escape(target_path)}"', rels_txt)
                                    if rid_match:
                                        rid = rid_match.group(1)
                                        wb_txt = (extract_dir / 'xl' / 'workbook.xml').read_text(encoding='utf-8')
                                        sheet_match = re.search(rf'<sheet[^>]*name="([^"]+)"[^>]*r:id="{rid}"', wb_txt)
                                        if sheet_match:
                                            sheet_name = sheet_match.group(1)
                                    break
                        
                        if sheet_name:
                            # Build formula using user's proven LET+RECHERCHE+INDEX pattern
                            # This handles header detection and finds last non-empty row automatically
                            # French: LET(col;'Sheet'!Col:Col;der;RECHERCHE(2;1/(col<>"");LIGNE(col));plage;INDEX(col;2):INDEX(col;der);plage)
                            formula = (
                                f"LET(col;'{sheet_name}'!{target_col_str}:{target_col_str};"
                                f"der;RECHERCHE(2;1/(col<>\"\");LIGNE(col));"
                                f"plage;INDEX(col;2):INDEX(col;der);"
                                f"plage)"
                            )
                        else:
                            formula = f"UNIQUE({source_ref})"
                    else:
                        formula = f"UNIQUE({source_ref})"
                else:
                        formula = f"LET(col;'{source_ref}';der;RECHERCHE(2;1/(col<>\"\");LIGNE(col));plage;INDEX(col;2):INDEX(col;der);plage)"
        else:
            # Sheet!Col:Col format - use LET+RECHERCHE to find last row
            parts = source_ref.split("!")
            sheet_name = parts[0].strip("'")
            col_ref = parts[1].replace("$", "")
            
            # French: LET(col;'Sheet'!A:A;der;RECHERCHE(2;1/(col<>"");LIGNE(col));plage;INDEX(col;2):INDEX(col;der);plage)
            formula = (
                f"LET(col;'{sheet_name}'!{col_ref};"
                f"der;RECHERCHE(2;1/(col<>\"\");LIGNE(col));"
                f"plage;INDEX(col;2):INDEX(col;der);"
                f"plage)"
            )
        try:
            formula = _translate_formula_to_french(formula)
        except Exception:
            # fallback to original if translation fails
            pass

        # Step 5: Find next sheet number and create sheet XML filename
        new_sheet_num = len(sheets.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet")) + 1
        sheet_xml_filename = f"sheet{new_sheet_num}.xml"
        
        # Step 6: Clone an existing VALID sheet as template (not sheet1 which is huge)
        # Use sheet8 (the Test sheet - small and valid) as template
        # This preserves all Excel internal validation metadata
        sheet_template_path = extract_dir / "xl" / "worksheets" / "sheet8.xml"
        if not sheet_template_path.exists():
            # Fallback: use sheet1 but we'll be more careful
            sheet_template_path = extract_dir / "xl" / "worksheets" / "sheet1.xml"
        
        sheet_template_content = sheet_template_path.read_text(encoding='utf-8')
        
        # Replace the worksheet UID with a new unique one
        sheet_xml = re.sub(r'xr:uid="\{[A-F0-9\-]+\}"', f'xr:uid="{{00000000-0000-0000-0000-000000000000}}"', sheet_template_content)
        
        # Replace ONLY the sheetData with our minimal content (keep everything else)
        match = re.search(r'<sheetData>.*?</sheetData>', sheet_xml, re.DOTALL)
        if not match:
            raise ValueError("Could not find sheetData in template sheet")
        
        # Build minimal sheetData for our 2-row formula sheet
        new_sheet_data = f'''<sheetData>
    <row r="1" spans="1:2">
      <c r="A1" t="str">
        <v>Id</v>
      </c>
      <c r="B1" t="str">
        <v>{escape(where_col)}</v>
      </c>
    </row>
    <row r="2" spans="1:2">
      <c r="A2"><f>{escape(formula)}</f><v></v></c>
      <c r="B2"/>
    </row>
  </sheetData>'''
        
        # Replace sheetData while preserving all other elements
        sheet_xml = sheet_xml[:match.start()] + new_sheet_data + sheet_xml[match.end():]
        
        # Update dimension to reflect actual content (2 rows, 2 columns)
        sheet_xml = re.sub(r'<dimension ref="[^"]*"', '<dimension ref="A1:B2"', sheet_xml)
        
        # Clean up view settings
        sheet_xml = re.sub(r'topLeftCell="[^"]*"', 'topLeftCell="A1"', sheet_xml)
        sheet_xml = re.sub(r'activeCell="[^"]*"', 'activeCell="A1"', sheet_xml)
        sheet_xml = re.sub(r'sqref="[^"]*"', 'sqref="A1"', sheet_xml)
        sheet_xml = re.sub(r'\stabSelected="1"', '', sheet_xml)

        sheet_xml_path = extract_dir / "xl" / "worksheets" / sheet_xml_filename
        sheet_xml_path.write_text(sheet_xml, encoding='utf-8')
        
        # Step 7: Update [Content_Types].xml to register new sheet
        content_types_path = extract_dir / "[Content_Types].xml"
        ct_content = content_types_path.read_text(encoding='utf-8')
        
        # Add Override for new sheet before closing </Types>
        new_override = f'<Override PartName="/xl/worksheets/{sheet_xml_filename}" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        ct_content = ct_content.replace('</Types>', f'{new_override}</Types>')
        content_types_path.write_text(ct_content, encoding='utf-8')
        
        # Step 8: Update workbook.xml.rels by text manipulation (preserve exact formatting)
        rels_file = extract_dir / "xl" / "_rels" / "workbook.xml.rels"
        rels_content = rels_file.read_text(encoding='utf-8')
        
        # Find max rId
        max_rid = 0
        for match in re.finditer(r'Id="rId(\d+)"', rels_content):
            max_rid = max(max_rid, int(match.group(1)))
        
        new_rId = max_rid + 1
        
        # Insert new relationship before closing </Relationships>
        new_rel_xml = f'  <Relationship Id="rId{new_rId}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/{sheet_xml_filename}"/>\n'
        rels_content = rels_content.replace('</Relationships>', f'{new_rel_xml}</Relationships>')
        rels_file.write_text(rels_content, encoding='utf-8')
        
        # Step 9: Update workbook.xml by text manipulation (preserve exact formatting)
        wb_content = wb_xml_path.read_text(encoding='utf-8')
        
        # Find max sheetId from text (more reliable than ElementTree)
        max_sheet_id = 0
        for match in re.finditer(r'sheetId="(\d+)"', wb_content):
            max_sheet_id = max(max_sheet_id, int(match.group(1)))
        
        new_sheet_id = max_sheet_id + 1
        
        # Insert new sheet element before closing </sheets>
        new_sheet_xml = f'  <sheet name="{escape(ds_name)}" sheetId="{new_sheet_id}" r:id="rId{new_rId}"/>\n'
        wb_content = wb_content.replace('</sheets>', f'{new_sheet_xml}</sheets>')
        
        # CRITICAL: Regenerate documentId to signal Excel that workbook was modified
        # This prevents Excel from marking the workbook as corrupt
        import uuid
        old_guid_match = re.search(r'documentId="8_\{[A-F0-9\-]+\}"', wb_content)
        if old_guid_match:
            new_guid = str(uuid.uuid4()).upper()
            new_doc_id = f'documentId="8_{{{new_guid}}}"'
            wb_content = re.sub(r'documentId="8_\{[A-F0-9\-]+\}"', new_doc_id, wb_content)
        
        wb_xml_path.write_text(wb_content, encoding='utf-8')
        
        # Step 10: Re-package as ZIP without openpyxl serialization
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            for fpath in extract_dir.rglob('*'):
                if fpath.is_file():
                    arcname = fpath.relative_to(extract_dir)
                    zip_out.write(fpath, arcname)
