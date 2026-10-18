"""Fill mapped cells in the original XLSX without reserializing worksheet XML.

Preserves namespace declarations, drawings, formulas, styles and all other ZIP parts.
"""
from pathlib import Path
from xml.sax.saxutils import escape
import io
import re
import zipfile

FIELDS = {
    'event_name': 'C8', 'event_dates': 'C9', 'event_time': 'C10',
    'event_place': 'C11', 'org_name': 'C31', 'org_address': 'C32',
    'org_tax_code': 'C33', 'org_phone': 'C34', 'org_email': 'G34',
    'reference_phone': 'C35', 'event_description': 'A38',
}
SHEET = 'xl/worksheets/sheet1.xml'

def render_excel(template: Path, values: dict) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(template, 'r') as original, zipfile.ZipFile(output, 'w') as result:
        for info in original.infolist():
            content = original.read(info.filename)
            if info.filename == SHEET:
                xml = content.decode('utf-8')
                for key, address in FIELDS.items():
                    value = values.get(key)
                    if value is None or not str(value).strip():
                        continue
                    # All mapped cells already exist in the original template.
                    # Replace the cell only: keep existing style and relationships.
                    pattern = re.compile(
                        r'(<c\\s+[^>]*\\br="' + re.escape(address) +
                        r'"[^>]*)(/>)'
                        r'|(<c\\s+[^>]*\\br="' + re.escape(address) +
                        r'"[^>]*>)(.*?)(</c>)', re.DOTALL
                    )
                    def replace(match):
                        attrs = match.group(1) or match.group(3)
                        attrs = re.sub(r'\\s+t="[^"]*"', '', attrs)
                        text = escape(str(value)[:2000], {'"': '&quot;', "'": '&apos;'})
                        return attrs + ' t="inlineStr"><is><t>' + text + '</t></is></c>'
                    xml, changes = pattern.subn(replace, xml, count=1)
                    if changes != 1:
                        raise ValueError('Excel template cell missing: ' + address)
                content = xml.encode('utf-8')
            result.writestr(info, content)
    return output.getvalue()
