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
# Values entered by the organizer, not by CRI coordinators.
NUMERIC_FIELDS = {'participants_athletes':'B94','participants_public':'D94','children':'F94','elderly':'H94','disabled':'J94'}
RECURRENCE={'Annuale':102,'Mensile':103,'Giornaliero':104,'Occasionale':105}
EVENT_TYPE={'Religioso':106,'Sportivo':107,'Intrattenimento':108,'Politico/sociale':109,'Concerto pop/rock':110}
RISK_FLAGS={
 'Prevista vendita/consumo di alcool':111,'Possibile consumo di droghe':112,
 'Presenza categorie fragili':113,'Evento ampiamente pubblicizzato':114,
 'Presenza figure politiche/religiose':115,'Possibili difficoltà nella viabilità':116,
 'Tensioni socio-politiche':117,'Ambiente acquatico':123,
 'Palco o ponteggio temporaneo':133,'Presenza di recinzioni':130,
 'Servizi igienici':134,'Disponibilità acqua':135,
}
LOCATION_FLAGS={'Al chiuso':96,"All'aperto":96,'Percorso isolato':96,'Percorso su strada':96}
def input_cells(values):
    cells={address:('text',values[key]) for key,address in FIELDS.items() if values.get(key) is not None and str(values[key]).strip()}
    for key,address in NUMERIC_FIELDS.items():
        if values.get(key) is not None:cells[address]=('number',int(values[key]))
    # The check marks belong to cells immediately before SI / NO captions.
    if 'road_closure' in values:
        cells['G43' if values['road_closure'] else 'I43']=('text','X')
    if values.get('recurrence') in RECURRENCE:cells['I'+str(RECURRENCE[values['recurrence']])]=('number',1)
    if values.get('event_type') in EVENT_TYPE:cells['I'+str(EVENT_TYPE[values['event_type']])]=('number',1)
    risks=set(values.get('risk_options') or [])
    for label,row in RISK_FLAGS.items():
        if label in risks:cells['I'+str(row)]=('number',1)
    return cells


def render_excel(template: Path, values: dict) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(template, 'r') as original, zipfile.ZipFile(output, 'w') as result:
        for info in original.infolist():
            content = original.read(info.filename)
            if info.filename == SHEET:
                xml = content.decode('utf-8')
                for address, (kind, value) in input_cells(values).items():
                    # All mapped cells already exist in the original template.
                    # Replace the cell only: keep existing style and relationships.
                    pattern = re.compile(
                        r'(<c\s+[^>]*\br="' + re.escape(address) +
                        r'"[^>]*)(/>)'
                        r'|(<c\s+[^>]*\br="' + re.escape(address) +
                        r'"[^>]*>)(.*?)(</c>)', re.DOTALL
                    )
                    def replace(match):
                        attrs = (match.group(1) or match.group(3)).rstrip('>')
                        attrs = re.sub(r'\s+t="[^"]*"', '', attrs)
                        text = escape(str(value)[:2000], {'"': '&quot;', "'": '&apos;'})
                        return (attrs + '><v>' + str(value) + '</v></c>') if kind=='number' else (attrs + ' t="inlineStr"><is><t>' + text + '</t></is></c>')
                    xml, changes = pattern.subn(replace, xml, count=1)
                    if changes != 1:
                        raise ValueError('Excel template cell missing: ' + address)
                content = xml.encode('utf-8')
            result.writestr(info, content)
    return output.getvalue()
