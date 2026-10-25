from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

path=Path(__file__).resolve().parents[1]/"app/templates/piano_sanitario_2026.xlsx"
q="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
with ZipFile(path) as z:
    shared=[]
    if "xl/sharedStrings.xml" in z.namelist():
        r=ET.fromstring(z.read("xl/sharedStrings.xml"))
        shared=["".join(t.text or "" for t in x.findall(".//"+q+"t")) for x in r.findall(q+"si")]
    sheet=ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    for row in sheet.findall(".//"+q+"sheetData/"+q+"row"):
        number=int(row.attrib["r"])
        if number>180:break
        parts=[]
        for c in row.findall(q+"c"):
            ref=c.attrib.get("r","")
            v=c.find(q+"v")
            formula=c.find(q+"f")
            ins=c.find(q+"is")
            value=v.text if v is not None else ""
            if c.attrib.get("t")=="s" and value and value.isdigit():
                value=shared[int(value)]
            elif c.attrib.get("t")=="inlineStr" and ins is not None:
                value="".join(ins.itertext())
            if value or formula is not None:
                value=(value or ("FORMULA "+(formula.text or "")))[:75]
                parts.append(ref+":"+value.replace("\n"," "))
        if parts:print("ROW",number,"|".join(parts[:24]))
