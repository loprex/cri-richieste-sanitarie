"""Regressions for Allegato 4 fields, Excel and historical reuse.

Uses synthetic organizer details; never connects to a running CRI instance.
"""
from pathlib import Path
from zipfile import ZipFile
import io
import xml.etree.ElementTree as ET

from app.excel import render_excel, input_cells, _supplement_rows

TEMPLATE=Path(__file__).resolve().parents[1]/'app'/'templates'/'piano_sanitario_2026.xlsx'
VALUES={
 'org_name':'Associazione Esempio & Soci','org_contact':'Mario Rossi',
 'org_first_name':'Mario','org_last_name':'Rossi','org_address':'Via Test 10, Venezia',
 'org_tax_code':'','org_vat':'','org_sdi':'XYZ1234',
 'org_phone':'0410000000','org_email':'persona@example.com','org_pec':'pec@example.com',
 'event_name':'Evento prova','event_city':'Venezia',
 'event_slots':[{'date':'2027-05-20','start':'09:00','end':'18:00'}],
 'event_dates':'2027-05-20','event_time':'09:00-18:00',
 'event_place':'Via Prova 1, Venezia',
 'event_description':'Descrizione lunga per il test tecnico',
 'reference_name':'Referente Test','reference_phone':'3400000000',
 'participants_athletes':25,'participants_public':500,'children':5,'elderly':12,'disabled':3,
 'event_type':'Sportivo','recurrence':'Annuale','road_closure':True,
 'road_documents':'Da trasmettere al Comitato','event_pause':'Pausa pranzo 13:00-14:00',
 'location_type':'Percorso su strada','venue_context':['In città'],
 'venue_features':['Percorso su strada','Recinzioni temporanee',
                   'Ponteggio temporaneo, palco o coperture'],
 'venue_logistics':['Servizi igienici disponibili',"Disponibilità d'acqua",'Punto di ristoro'],
 'crowd_age_profile':'25-65 anni','crowd_density':'Media (3-4 persone/m²)',
 'crowd_mood':'Rilassato','crowd_position':'In piedi',
 'involved_entities':['Protezione civile','Vigili del fuoco','Forze dell’ordine'],
 'involved_entities_other':'','event_duration_bracket':'<12 ore',
 'participants_estimate_bracket':'<25.000',
 'risk_options':['Possibile consumo di droghe'],
 'additional_notes':'Dati sintetici','privacy_ack':True,'declaration':True,
}


def test_export_contains_every_organizer_field_without_dropping_values():
    rows=_supplement_rows(VALUES)
    named={label for label,_ in rows}
    labels={
      'Nome referente','Cognome referente','Partita IVA','Codice univoco SDI',
      'PEC','Caratteristiche del luogo','Densità per m²','Posizione del pubblico',
      'Altri enti coinvolti','Documentazione viabilità','Pause previste',
    }
    assert labels<=named
    generated=render_excel(TEMPLATE,VALUES)
    with ZipFile(io.BytesIO(generated)) as z:
        workbook=z.read('xl/workbook.xml').decode()
        assert 'Dati compilazione' in workbook
        attached=[n for n in z.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]
        assert len(attached)>=2
        supplemental=z.read(attached[-1]).decode()
        assert 'Associazione Esempio &amp; Soci' in supplemental
        assert 'Punto di ristoro' in supplemental
        assert 'Vigili del fuoco' in supplemental
        assert 'Media (3-4 persone/m²)' in supplemental
        assert 'Da trasmettere al Comitato' in supplemental
        for name in z.namelist():
            if name.endswith('.xml') or name.endswith('.rels'):
                ET.fromstring(z.read(name))


def test_export_preserves_original_files_formulas_and_main_sheet():
    generated=render_excel(TEMPLATE,VALUES)
    allowed_changes={
      '[Content_Types].xml','xl/workbook.xml','xl/_rels/workbook.xml.rels',
      'xl/worksheets/sheet1.xml',
    }
    with ZipFile(TEMPLATE) as source,ZipFile(io.BytesIO(generated)) as output:
        for part in source.namelist():
            if part not in allowed_changes:
                assert output.read(part)==source.read(part),part
        before=source.read('xl/worksheets/sheet1.xml')
        after=output.read('xl/worksheets/sheet1.xml')
        assert before.count(b'<f')==after.count(b'<f')
        assert before.count(b'</f>')==after.count(b'</f>')
        # Numeric data and reviewed mappings still populate the original layout.
        sheet=ET.fromstring(after)
        ns={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        for cell,value in {'B94':'25','D94':'500','F94':'5','H94':'12','J94':'3'}.items():
            elem=sheet.find(f".//x:c[@r='{cell}']/x:v",ns)
            assert elem is not None and elem.text==value,cell


def test_new_structured_risks_feed_existing_known_excel_flags():
    cells=input_cells(VALUES)
    assert cells['I130']==('number',1)  # temporary fencing
    assert cells['I133']==('number',1)  # stage
    assert cells['I134']==('number',1)  # bathrooms
    assert cells['I135']==('number',1)  # drinking water
    assert cells['I112']==('number',1)  # drugs
    assert cells['G43']==('text','X')   # road modification


def test_no_previous_event_can_reuse_protocol_dates_or_consents():
    main=Path(__file__).resolve().parents[1]/'app'/'main.py'
    source=main.read_text(encoding='utf-8')
    reuse=source.split('REUSABLE_EVENT_FIELDS=(',1)[1].split(')',1)[0]
    for forbidden in ('event_slots','event_dates','event_time','protocol_number',
                      'privacy_ack','declaration','org_email'):
        assert "'"+forbidden+"'" not in reuse
    for allowed in ('venue_features','crowd_density','involved_entities',
                    'org_first_name','org_last_name','event_pause'):
        assert "'"+allowed+"'" in reuse
