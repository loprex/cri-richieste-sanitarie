"""Surgical XLSX XML update: preserves workbook's existing formulas, merges and styling.
Only mapped user-input cells are modified; never touch clinical planning/risk formulas.
"""
from pathlib import Path
import io,zipfile,xml.etree.ElementTree as ET
from datetime import datetime, timezone
NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
ET.register_namespace('',NS)
# All targets are the top-left cell of an existing merged range (where merged).
FIELDS={
 'event_name':'C8','event_dates':'C9','event_time':'C10','event_place':'C11',
 'org_name':'C31','org_address':'C32','org_tax_code':'C33',
 'org_phone':'C34','org_email':'G34','reference_phone':'C35',
 'event_description':'A38',
}
# Do not force the road-closure yes/no choice into the template: source uses checkboxes/graphic cells.
def render_excel(template:Path,values:dict)->bytes:
    raw=template.read_bytes(); out=io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw),'r') as source,zipfile.ZipFile(out,'w') as target:
        for item in source.infolist():
            content=source.read(item.filename)
            if item.filename=='xl/worksheets/sheet1.xml':
                root=ET.fromstring(content)
                sheet=root.find(f'{{{NS}}}sheetData')
                by_row={int(r.attrib['r']):r for r in sheet.findall(f'{{{NS}}}row')}
                for key,addr in FIELDS.items():
                    v=values.get(key)
                    if v is None or str(v).strip()=='':continue
                    col=''.join(x for x in addr if x.isalpha()); row=int(''.join(x for x in addr if x.isdigit()))
                    r=by_row.get(row)
                    if r is None:continue
                    cell=next((x for x in r.findall(f'{{{NS}}}c') if x.attrib.get('r')==addr),None)
                    if cell is None:
                        cell=ET.Element(f'{{{NS}}}c',{'r':addr})
                        # Insert in physical column order, without breaking existing formatting.
                        def number(c):
                            n=0
                            for s in ''.join(z for z in c.attrib['r'] if z.isalpha()):n=n*26+ord(s)-64
                            return n
                        index=next((i for i,c in enumerate(r) if c.tag==f'{{{NS}}}c' and number(c)>number(cell)),len(r))
                        r.insert(index,cell)
                    for n in list(cell):
                        if n.tag in (f'{{{NS}}}v',f'{{{NS}}}is',f'{{{NS}}}f'):cell.remove(n)
                    cell.set('t','inlineStr')
                    inline=ET.SubElement(cell,f'{{{NS}}}is')
                    text=ET.SubElement(inline,f'{{{NS}}}t')
                    text.text=str(v)[:2000]
                    if text.text and (text.text[0].isspace() or text.text[-1].isspace()):text.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
                content=ET.tostring(root,encoding='utf-8',xml_declaration=True)
            target.writestr(item,content)
    return out.getvalue()
