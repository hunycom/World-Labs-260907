#!/usr/bin/env python3
"""
scripts/convert_report_to_docs.py

Converts a markdown document (specifically docs/p3/P3_CLOSE_v0.md)
into:
  - docs/p3/P3_CLOSE_v0.docx (WordprocessingML in ZIP)
  - docs/p3/P3_CLOSE_v0.pdf (PDF 1.4 pure python generator)
"""

import sys
import io
import re
import zipfile
from pathlib import Path
import xml.sax.saxutils as saxutils

ROOT_DIR = Path(__file__).resolve().parent.parent

def escape_xml(s: str) -> str:
    return saxutils.escape(s)

def markdown_to_docx(md_text: str, out_path: Path):
    """
    Builds a standard .docx file in pure Python from markdown lines.
    Supports headings (#..#####), bullet items (- ), paragraphs, and tables (|..|).
    """
    lines = md_text.splitlines()
    body_xml_parts = []
    
    in_table = False
    table_rows = []
    
    def flush_table():
        nonlocal in_table, table_rows, body_xml_parts
        if not table_rows:
            in_table = False
            return
        
        # Determine number of columns
        num_cols = max(len(r) for r in table_rows)
        # 9000 dxa (~6.25 inches) total width
        col_w = 9000 // max(1, num_cols)
        
        tbl_xml = [
            '<w:tbl>',
            '<w:tblPr>',
            '<w:tblStyle w:val="TableGrid"/>',
            '<w:tblW w:w="9000" w:type="dxa"/>',
            '<w:tblBorders>',
            '<w:top w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>',
            '<w:left w:val="none"/>',
            '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>',
            '<w:right w:val="none"/>',
            '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="EEEEEE"/>',
            '<w:insideV w:val="none"/>',
            '</w:tblBorders>',
            '</w:tblPr>'
        ]
        
        for r_idx, row in enumerate(table_rows):
            is_header = (r_idx == 0)
            tbl_xml.append('<w:tr>')
            if is_header:
                tbl_xml.append('<w:trPr><w:tblHeader/></w:trPr>')
            for cell in row:
                tbl_xml.append(f'<w:tc><w:tcPr><w:tcW w:w="{col_w}" w:type="dxa"/>')
                if is_header:
                    tbl_xml.append('<w:shd w:val="clear" w:color="auto" w:fill="F0F4F8"/>')
                tbl_xml.append('</w:tcPr>')
                clean_cell = re.sub(r'[*`_]', '', cell.strip())
                b_tag = '<w:b/>' if is_header else ''
                tbl_xml.append(f'<w:p><w:pPr><w:spacing w:before="60" w:after="60"/></w:pPr><w:r><w:rPr>{b_tag}</w:rPr><w:t>{escape_xml(clean_cell)}</w:t></w:r></w:p>')
                tbl_xml.append('</w:tc>')
            # Fill missing cells
            for _ in range(num_cols - len(row)):
                tbl_xml.append(f'<w:tc><w:tcPr><w:tcW w:w="{col_w}" w:type="dxa"/></w:tcPr><w:p/></w:tc>')
            tbl_xml.append('</w:tr>')
            
        tbl_xml.append('</w:tbl>')
        body_xml_parts.append(''.join(tbl_xml))
        table_rows = []
        in_table = False

    for line in lines:
        stripped = line.strip()
        
        # Table row
        if stripped.startswith('|') and stripped.endswith('|'):
            # Check if separator row like |---|---|
            inner = stripped[1:-1].replace('-', '').replace(':', '').replace('|', '').strip()
            if not inner:
                continue # Skip markdown separator row
            
            in_table = True
            cells = [c.strip() for c in stripped[1:-1].split('|')]
            table_rows.append(cells)
            continue
        elif in_table:
            flush_table()
            
        if not stripped:
            continue
            
        # Headings
        if stripped.startswith('#'):
            level = len(stripped.split()[0])
            htext = stripped.lstrip('#').strip()
            clean_htext = re.sub(r'[*`_]', '', htext)
            style = f"Heading{min(level, 5)}"
            sz = max(20, 36 - level * 4) # half-points
            p_xml = (
                f'<w:p>'
                f'<w:pPr><w:pStyle w:val="{style}"/><w:spacing w:before="240" w:after="120"/></w:pPr>'
                f'<w:r><w:rPr><w:b/><w:sz w:val="{sz}"/><w:color w:val="1A365D"/></w:rPr>'
                f'<w:t>{escape_xml(clean_htext)}</w:t></w:r>'
                f'</w:p>'
            )
            body_xml_parts.append(p_xml)
        elif stripped.startswith('- ') or stripped.startswith('* '):
            item_text = stripped[2:].strip()
            clean_item = re.sub(r'[*`_]', '', item_text)
            p_xml = (
                f'<w:p>'
                f'<w:pPr><w:ind w:left="360"/><w:spacing w:before="40" w:after="40"/></w:pPr>'
                f'<w:r><w:rPr><w:color w:val="2B6CB0"/></w:rPr><w:t>• </w:t></w:r>'
                f'<w:r><w:t>{escape_xml(clean_item)}</w:t></w:r>'
                f'</w:p>'
            )
            body_xml_parts.append(p_xml)
        elif stripped.startswith('```'):
            continue
        else:
            clean_p = re.sub(r'[*`_]', '', stripped)
            p_xml = (
                f'<w:p>'
                f'<w:pPr><w:spacing w:before="60" w:after="80"/><w:line w:line="276" w:lineRule="auto"/></w:pPr>'
                f'<w:r><w:t>{escape_xml(clean_p)}</w:t></w:r>'
                f'</w:p>'
            )
            body_xml_parts.append(p_xml)
            
    if in_table:
        flush_table()

    body_content = ''.join(body_xml_parts)
    
    document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body_content}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
    </w:sectPr>
  </w:body>
</w:document>'''

    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''

    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for arcname, data in [
            ('[Content_Types].xml', content_types),
            ('_rels/.rels', rels),
            ('word/document.xml', document_xml)
        ]:
            zinfo = zipfile.ZipInfo(filename=arcname, date_time=(2026, 9, 7, 0, 0, 0))
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zinfo, data)

    print(f"[+] Successfully generated DOCX: {out_path} ({out_path.stat().st_size:,} bytes)")



def markdown_to_pdf(md_text: str, out_path: Path):
    """
    Builds a standard PDF 1.4 document in pure Python.
    Generates multiple pages with margins, running headers, and formatted text/tables.
    """
    lines = md_text.splitlines()
    
    pages_ops = [] # list of operator strings for each page
    current_ops = []
    
    # Page setup: Letter size: 612 x 792 points
    # Margin: 45 pt left, right 567 pt. Top: 745 pt, Bottom: 45 pt.
    y = 740
    page_num = 1
    
    def new_page():
        nonlocal y, page_num, current_ops, pages_ops
        # Page footer
        current_ops.append(f"BT /F1 9 Tf 280 25 Td ({page_num}) Tj ET\n")
        pages_ops.append("".join(current_ops))
        current_ops = []
        page_num += 1
        y = 740
        # Header on subsequent pages
        current_ops.append("BT /F1 8 Tf 45 765 Td (Spark.js Spatial AI - P3-05 Closeout Document v0) Tj ET\n")
        current_ops.append("0.8 G 0.5 w 45 760 m 567 760 l S 0 G\n")
        
    def escape_pdf_str(s: str) -> str:
        # Normalize non-ascii to ascii transliteration for PDF Type 1 Helvetica font
        res = []
        for ch in s:
            if ch in '()\\':
                res.append('\\' + ch)
            elif ord(ch) < 128:
                res.append(ch)
            else:
                # Transliterate or encode safely
                res.append(ch)
        # Type 1 standard fonts in PDF 1.4 expect octal or latin-1/ascii
        # Convert any unicode to bytes safe representation
        raw_b = "".join(res).encode('latin-1', 'replace').decode('latin-1')
        return raw_b.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

    for line in lines:
        stripped = line.strip()
        if not stripped:
            y -= 6
            continue
            
        if y < 60:
            new_page()
            
        if stripped.startswith('```'):
            continue
            
        clean_line = re.sub(r'[*`_]', '', stripped)
        
        if clean_line.startswith('#'):
            level = len(clean_line.split()[0])
            htext = clean_line.lstrip('#').strip()
            font_sz = max(10, 16 - level)
            y -= (font_sz + 6)
            current_ops.append(f"BT /F2 {font_sz} Tf 45 {y} Td ({escape_pdf_str(htext)}) Tj ET\n")
            y -= 4
        elif clean_line.startswith('- ') or clean_line.startswith('* '):
            item = clean_line[2:].strip()
            font_sz = 9
            y -= (font_sz + 4)
            # Bullet
            current_ops.append(f"BT /F2 {font_sz} Tf 45 {y} Td (-) Tj /F1 {font_sz} Tf 55 {y} Td ({escape_pdf_str(item[:110])}) Tj ET\n")
            if len(item) > 110:
                y -= (font_sz + 3)
                current_ops.append(f"BT /F1 {font_sz} Tf 55 {y} Td ({escape_pdf_str(item[110:220])}) Tj ET\n")
        elif clean_line.startswith('|'):
            # Table row
            if '---' in clean_line:
                continue
            cells = [c.strip() for c in clean_line.strip('|').split('|')]
            font_sz = 8
            y -= (font_sz + 5)
            # Draw row
            col_x = 45
            w_col = 520 // max(1, len(cells))
            for c in cells:
                current_ops.append(f"BT /F1 {font_sz} Tf {col_x} {y} Td ({escape_pdf_str(c[:25])}) Tj ET\n")
                col_x += w_col
        else:
            # Paragraph
            font_sz = 9
            # Word wrap around 110 chars
            words = clean_line.split()
            cur_line = ""
            for w in words:
                if len(cur_line) + len(w) + 1 <= 110:
                    cur_line += (" " if cur_line else "") + w
                else:
                    y -= (font_sz + 3)
                    if y < 60:
                        new_page()
                    current_ops.append(f"BT /F1 {font_sz} Tf 45 {y} Td ({escape_pdf_str(cur_line)}) Tj ET\n")
                    cur_line = w
            if cur_line:
                y -= (font_sz + 3)
                current_ops.append(f"BT /F1 {font_sz} Tf 45 {y} Td ({escape_pdf_str(cur_line)}) Tj ET\n")
                
    # Finish last page
    current_ops.append(f"BT /F1 9 Tf 280 25 Td ({page_num}) Tj ET\n")
    pages_ops.append("".join(current_ops))
    
    # Assemble PDF structure
    # Objects:
    # 1: Catalog
    # 2: Pages
    # 3: Font F1 (Helvetica)
    # 4: Font F2 (Helvetica-Bold)
    # 5 .. 5 + 2*N - 1: Page and Contents
    total_pages = len(pages_ops)
    
    obj_offsets = {}
    buf = io.BytesIO()
    
    def write_bytes(b: bytes):
        pos = buf.tell()
        buf.write(b)
        return pos

    write_bytes(b"%PDF-1.4\n")
    
    # 1: Catalog
    obj_offsets[1] = write_bytes(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    
    # Page object IDs: 5, 7, 9, ...
    kids_refs = " ".join(f"{5 + i * 2} 0 R" for i in range(total_pages))
    # 2: Pages
    obj_offsets[2] = write_bytes(f"2 0 obj\n<< /Type /Pages /Kids [ {kids_refs} ] /Count {total_pages} >>\nendobj\n".encode())
    
    # 3: Font F1
    obj_offsets[3] = write_bytes(b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    # 4: Font F2
    obj_offsets[4] = write_bytes(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n")
    
    for i, ops in enumerate(pages_ops):
        page_id = 5 + i * 2
        content_id = page_id + 1
        
        ops_bytes = ops.encode('latin-1')
        
        # Page obj
        obj_offsets[page_id] = write_bytes(
            f"{page_id} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [ 0 0 612 792 ] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>\nendobj\n".encode()
        )
        # Content obj
        obj_offsets[content_id] = write_bytes(
            f"{content_id} 0 obj\n<< /Length {len(ops_bytes)} >>\nstream\n".encode() + ops_bytes + b"\nendstream\nendobj\n"
        )
        
    xref_offset = buf.tell()
    num_objs = 4 + total_pages * 2
    buf.write(f"xref\n0 {num_objs + 1}\n0000000000 65535 f \n".encode())
    for oid in range(1, num_objs + 1):
        offset = obj_offsets[oid]
        buf.write(f"{offset:010d} 00000 n \n".encode())
        
    buf.write(f"trailer\n<< /Size {num_objs + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode())
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(buf.getvalue())
    print(f"[+] Successfully generated PDF: {out_path} ({out_path.stat().st_size:,} bytes, {total_pages} pages)")

def main():
    if len(sys.argv) > 1:
        target_md = Path(sys.argv[1])
        if not target_md.is_absolute():
            target_md = ROOT_DIR / target_md
    else:
        target_md = ROOT_DIR / "docs" / "p3" / "P3_CLOSE_v1draft.md"
        if not target_md.exists():
            target_md = ROOT_DIR / "docs" / "p3" / "P3_CLOSE_v0.md"

    if not target_md.exists():
        print(f"[-] Target markdown not found: {target_md}")
        sys.exit(1)
        
    md_content = target_md.read_text(encoding="utf-8")
    
    docx_path = target_md.with_suffix(".docx")
    pdf_path = target_md.with_suffix(".pdf")
    
    markdown_to_docx(md_content, docx_path)
    markdown_to_pdf(md_content, pdf_path)

if __name__ == "__main__":
    main()
