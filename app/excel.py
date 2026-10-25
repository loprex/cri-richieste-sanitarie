"""Populate the original CRI medical plan without rewriting its formulas or styling.

Only reviewed, existing cells on the first sheet are edited. All submitted
organizer fields (including newly collected Allegato 4 information) are also
written to an additive worksheet, so no field is silently discarded.
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
NUMERIC_FIELDS = {
    'participants_athletes': 'B94', 'participants_public': 'D94',
    'children': 'F94', 'elderly': 'H94', 'disabled': 'J94',
}
RECURRENCE = {'Annuale':102, 'Mensile':103, 'Giornaliero':104, 'Occasionale':105}
EVENT_TYPE = {
    'Religioso':106, 'Sportivo':107, 'Intrattenimento':108,
    'Politico/sociale':109, 'Concerto pop/rock':110,
}
RISK_FLAGS = {
    'Prevista vendita/consumo di alcool':111, 'Possibile consumo di droghe':112,
    'Presenza categorie fragili':113, 'Evento ampiamente pubblicizzato':114,
    'Presenza figure politiche/religiose':115, 'Possibili difficoltà nella viabilità':116,
    'Tensioni socio-politiche':117, 'Ambiente acquatico':123,
    'Palco o ponteggio temporaneo':133, 'Presenza di recinzioni':130,
    'Servizi igienici':134, 'Disponibilità acqua':135,
}

# The original template uses column I as the user selection: write 'x'.
# Column J holds formulas evaluating I; never write to J102:J153.
CONTEXT_FLAGS={
    'In città':121, 'In periferia/paesi o piccoli centri urbani':122,
    'In ambiente acquatico (lago, fiume, mare, piscina)':123,
    'Altro (montano, impervio o rurale)':124,
}
FEATURE_FLAGS={
    'Al coperto':125, "All'aperto":126,
    'Localizzato e ben definito':127, 'Esteso oltre un campo da calcio':128,
    'Non delimitato da recinzioni':129, 'Delimitato da recinzioni':130,
    'Presenza di scale in entrata e/o uscita':131, 'Recinzioni temporanee':132,
    'Ponteggio temporaneo, palco o coperture':133,
}
LOGISTICS_FLAGS={
    'Servizi igienici disponibili':134, "Disponibilità d'acqua":135,
    'Punto di ristoro':136,
}
DURATION_FLAGS={'<12 ore':118, '12 ore - 3 giorni':119, '>3 giorni':120}
PARTICIPANTS_FLAGS={
    '<25.000':138, '25.000-100.000':139,
    '100.000-500.000':140, '>500.000':141,
}
AGE_FLAGS={'25-65 anni':142, 'Sotto 25 o sopra 65 anni':143}
DENSITY_FLAGS={
    'Bassa (1-2 persone/m²)':144, 'Media (3-4 persone/m²)':145,
    'Alta (4-8 persone/m²)':146, 'Estrema (>8 persone/m²)':147,
}
MOOD_FLAGS={'Rilassato':148, 'Eccitato':149, 'Aggressivo':150}
POSITION_FLAGS={'Seduti':151, 'In parte seduti':152, 'In piedi':153}
LEGACY_LOCATION={'Al chiuso':125, "All'aperto":126}
LABELS = {
    'org_name':'Ragione sociale / ente', 'org_contact':'Nome completo del referente',
    'org_first_name':'Nome referente', 'org_last_name':'Cognome referente',
    'org_address':'Indirizzo sede legale', 'org_tax_code':'Codice fiscale',
    'org_vat':'Partita IVA', 'org_sdi':'Codice univoco SDI',
    'org_phone':'Telefono organizzatore', 'org_email':'Email',
    'org_pec':'PEC', 'event_name':'Denominazione evento',
    'event_city':'Comune evento', 'event_dates':'Date di svolgimento',
    'event_time':'Orari di svolgimento', 'event_slots':'Giornate e fasce orarie',
    'event_place':'Sede svolgimento', 'event_description':'Descrizione evento',
    'reference_name':'Referente sul posto', 'reference_phone':'Cellulare referente',
    'participants_athletes':'Atleti / partecipanti attivi',
    'participants_public':'Pubblico / spettatori', 'children':'Numero bambini',
    'elderly':'Numero anziani', 'disabled':'Numero persone con disabilità',
    'event_type':'Tipologia evento', 'recurrence':'Frequenza evento',
    'location_type':'Tipologia principale del luogo',
    'road_closure':'Modifica viabilità', 'road_documents':'Documentazione viabilità',
    'event_pause':'Pause previste', 'event_duration_bracket':'Durata evento (fascia)',
    'participants_estimate_bracket':'Stima partecipanti (fascia)',
    'venue_context':'Dove si verifica', 'venue_features':'Caratteristiche del luogo',
    'venue_logistics':'Logistica del posto', 'crowd_age_profile':'Età prevalente',
    'crowd_density':'Densità per m²', 'crowd_mood':'Condizione del pubblico',
    'crowd_position':'Posizione del pubblico',
    'involved_entities':'Altri enti coinvolti', 'involved_entities_other':'Altro ente',
    'risk_options':'Altre variabili / fattori di rischio',
    'additional_notes':'Note dell’organizzatore',
    'privacy_ack':'Presa visione informativa', 'declaration':'Dichiarazione finale',
}
GROUPS = [
    ('Organizzatore',('org_name','org_first_name','org_last_name','org_contact',
        'org_address','org_phone','org_email','org_pec','org_tax_code','org_vat','org_sdi')),
    ('Evento',('event_name','event_city','event_dates','event_time','event_slots',
        'event_place','event_description','reference_name','reference_phone',
        'event_type','recurrence','road_closure','road_documents','event_pause',
        'event_duration_bracket')),
    ('Partecipanti',('participants_athletes','participants_public','children','elderly',
        'disabled','participants_estimate_bracket','crowd_age_profile',
        'crowd_density','crowd_mood','crowd_position')),
    ('Luogo e logistica',('location_type','venue_context','venue_features','venue_logistics')),
    ('Rischio ed enti',('risk_options','involved_entities','involved_entities_other','additional_notes')),
    ('Dichiarazioni',('privacy_ack','declaration')),
]


def input_cells(values):
    cells={address:('text',values[key]) for key,address in FIELDS.items()
           if values.get(key) is not None and str(values[key]).strip()}
    for key,address in NUMERIC_FIELDS.items():
        if values.get(key) is not None:
            cells[address]=('number',int(values[key]))
    if 'road_closure' in values:
        cells['G43' if values['road_closure'] else 'I43']=('text','X')

    def flag(row):
        # J formulas use IF(I...=\"x\", score, 0): preserve them exactly.
        cells['I'+str(row)]=('text','x')

    for key,rows in (('recurrence',RECURRENCE),('event_type',EVENT_TYPE),
                     ('event_duration_bracket',DURATION_FLAGS),
                     ('participants_estimate_bracket',PARTICIPANTS_FLAGS),
                     ('crowd_age_profile',AGE_FLAGS),
                     ('crowd_density',DENSITY_FLAGS),
                     ('crowd_mood',MOOD_FLAGS),('crowd_position',POSITION_FLAGS),
                     ('location_type',LEGACY_LOCATION)):
        choice=values.get(key)
        if choice in rows:flag(rows[choice])

    for key,rows in (('venue_context',CONTEXT_FLAGS),
                     ('venue_features',FEATURE_FLAGS),
                     ('venue_logistics',LOGISTICS_FLAGS)):
        for choice in values.get(key) or []:
            if choice in rows:flag(rows[choice])

    # Original printable summary of venue and time (blanks verified in template).
    selected=set(values.get('venue_features') or [])
    if values.get('location_type'):selected.add(values['location_type'])
    location_cells={
        'Al chiuso':'B96','Al coperto':'B96',
        "All'aperto":'D96','Percorso isolato':'F96','Percorso su strada':'H96',
    }
    for key,address in location_cells.items():
        if key in selected:cells[address]=('text','X')
    if values.get('event_duration_bracket'):
        cells['B99']=('text',values['event_duration_bracket'])
    if values.get('event_pause'):
        cells['G99']=('text',values['event_pause'])
    for choice in values.get('risk_options') or []:
        if choice in RISK_FLAGS:flag(RISK_FLAGS[choice])
    if any(values.get(k,0)>0 for k in ('children','elderly','disabled')):
        flag(113)
    return cells


def _set_cell(xml, address, kind, value):
    pattern = re.compile(
        r'(<c\s+[^>]*\br="' + re.escape(address) + r'"[^>]*)(/>)'
        r'|(<c\s+[^>]*\br="' + re.escape(address) +
        r'"[^>]*>)(.*?)(</c>)', re.DOTALL
    )
    def replace(match):
        attrs = (match.group(1) or match.group(3)).rstrip('>')
        attrs = re.sub(r'\s+t="[^"]*"', '', attrs)
        raw = str(value)
        if kind == 'number':
            return attrs + '><v>' + raw + '</v></c>'
        content = escape(raw[:2000], {'"':'&quot;', "'":'&apos;'})
        return attrs + ' t="inlineStr"><is><t>' + content + '</t></is></c>'
    xml, changed = pattern.subn(replace, xml, count=1)
    if changed != 1:
        raise ValueError('Excel template cell missing: ' + address)
    return xml


def _display(value):
    if isinstance(value, bool):
        return 'Sì' if value else 'No'
    if isinstance(value, list):
        if all(isinstance(x,dict) for x in value):
            return '; '.join(' '.join(str(item.get(k,'')) for k in ('date','start','end'))
                             for item in value)
        return '; '.join(str(x) for x in value)
    return '' if value is None else str(value)


def _supplement_rows(values):
    rows = [('RACCOLTA DATI - ALLEGATO 4','Dati forniti dall’organizzatore; verificare prima dell’approvazione')]
    done=set()
    for heading,keys in GROUPS:
        rows.append((heading.upper(),''))
        for key in keys:
            if key in values:
                rows.append((LABELS.get(key,key),_display(values[key])))
                done.add(key)
    # Forward compatible: a future form field is never silently lost.
    extra=sorted(set(values)-done)
    if extra:
        rows.append(('ALTRE INFORMAZIONI',''))
        rows.extend((LABELS.get(key,key.replace('_',' ')),_display(values[key])) for key in extra)
    return rows


def _worksheet_xml(values):
    rows = _supplement_rows(values)
    def cell(column,number,value):
        encoded=escape(value[:32767], {'"':'&quot;', "'":'&apos;'})
        return (f'<c r="{column}{number}" t="inlineStr">'
                f'<is><t xml:space="preserve">{encoded}</t></is></c>')
    body=''.join(
        f'<row r="{i}">{cell("A",i,str(label))}{cell("B",i,str(value))}</row>'
        for i,(label,value) in enumerate(rows,1)
    )
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        '<cols><col min="1" max="1" width="39" customWidth="1"/>'
        '<col min="2" max="2" width="90" customWidth="1"/></cols>'
        f'<sheetData>{body}</sheetData></worksheet>').encode('utf-8')


def _insert_before(source, token, addition, part):
    if source.count(token)!=1:
        raise ValueError('Unexpected XLSX structure: ' + part)
    return source.replace(token, addition+token)


def render_excel(template: Path, values: dict) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(template,'r') as original:
        original_parts = set(original.namelist())
        numbers = [int(m.group(1)) for part in original_parts
                   if (m:=re.fullmatch(r'xl/worksheets/sheet(\d+)\.xml',part))]
        number=max(numbers,default=0)+1
        sheet_part=f'xl/worksheets/sheet{number}.xml'
        workbook=original.read('xl/workbook.xml').decode('utf-8')
        rels=original.read('xl/_rels/workbook.xml.rels').decode('utf-8')
        content_types=original.read('[Content_Types].xml').decode('utf-8')
        sheet_ids=[int(n) for n in re.findall(r'sheetId="(\d+)"',workbook)]
        rel_ids=[int(n) for n in re.findall(r'\bId="rId(\d+)"',rels)]
        rid='rId'+str(max(rel_ids,default=0)+1)
        sheet_id=max(sheet_ids,default=0)+1
        workbook=_insert_before(workbook,'</sheets>',
            f'<sheet name="Dati compilazione" sheetId="{sheet_id}" r:id="{rid}"/>',
            'workbook sheets')
        rels=_insert_before(rels,'</Relationships>',
            f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{number}.xml"/>',
            'workbook relationships')
        content_types=_insert_before(content_types,'</Types>',
            f'<Override PartName="/{sheet_part}" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>',
            'content types')
        with zipfile.ZipFile(output,'w') as result:
            for info in original.infolist():
                content=original.read(info.filename)
                if info.filename==SHEET:
                    xml=content.decode('utf-8')
                    for address,(kind,value) in input_cells(values).items():
                        xml=_set_cell(xml,address,kind,value)
                    content=xml.encode('utf-8')
                elif info.filename=='xl/workbook.xml':
                    content=workbook.encode('utf-8')
                elif info.filename=='xl/_rels/workbook.xml.rels':
                    content=rels.encode('utf-8')
                elif info.filename=='[Content_Types].xml':
                    content=content_types.encode('utf-8')
                result.writestr(info,content)
            result.writestr(sheet_part,_worksheet_xml(values),compress_type=zipfile.ZIP_DEFLATED)
    return output.getvalue()
