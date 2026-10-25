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
        # The I column contains weights (including negative protective factors).
        # A client answer must only ever change column J, never the weights.
        ns={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        original_sheet=ET.fromstring(before)
        exported_sheet=ET.fromstring(after)
        for row in range(102,154):
            path=f".//x:c[@r='I{row}']"
            before_cell=original_sheet.find(path,ns)
            after_cell=exported_sheet.find(path,ns)
            if before_cell is not None:
                assert ET.tostring(before_cell)==ET.tostring(after_cell),f'I{row}'

        # Numeric data and reviewed mappings still populate the original layout.
        sheet=ET.fromstring(after)
        ns={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        for cell,value in {'B94':'25','D94':'500','F94':'5','H94':'12','J94':'3'}.items():
            elem=sheet.find(f".//x:c[@r='{cell}']/x:v",ns)
            assert elem is not None and elem.text==value,cell


def test_new_structured_risks_feed_existing_known_excel_flags():
    cells=input_cells(VALUES)
    assert cells['J130']==('number',1)  # temporary fencing
    assert cells['J133']==('number',1)  # stage
    assert cells['J134']==('number',1)  # bathrooms
    assert cells['J135']==('number',1)  # drinking water
    assert cells['J112']==('number',1)  # drugs
    assert cells['G43']==('text','X')   # road modification
    assert cells['J102']==('number',1)  # yearly recurrence
    assert cells['J107']==('number',1)  # sport
    assert cells['J118']==('number',1)  # duration
    assert cells['J121']==('number',1)  # in city
    assert cells['J132']==('number',1)  # temporary fences (not J130)
    assert cells['J136']==('number',1)  # refreshment point
    assert cells['J138']==('number',1)  # estimated crowd
    assert cells['J142']==('number',1)  # audience age
    assert cells['J145']==('number',1)  # medium crowd density
    assert cells['J148']==('number',1)  # relaxed
    assert cells['J153']==('number',1)  # standing
    assert cells['H96']==('text','X')   # street venue
    assert cells['B99']==('text','<12 ore')
    assert cells['G99']==('text','Pausa pranzo 13:00-14:00')
    assert all(not key.startswith('I1') or key=='I43' for key in cells)



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


def test_form_has_all_backend_fields_and_multi_select_serialization():
    from app.main import Submission
    model=Submission.model_validate(VALUES)
    assert model.org_contact=='Mario Rossi'
    assert model.event_duration_bracket=='<12 ore'
    assert model.participants_estimate_bracket=='<25.000'
    assert model.venue_features==VALUES['venue_features']
    assert model.involved_entities==VALUES['involved_entities']

    root=Path(__file__).resolve().parents[1]/'app'/'static'
    html=(root/'form.html').read_text()
    js=(root/'form.js').read_text()
    for key in ('org_first_name','org_last_name','crowd_age_profile',
                'crowd_density','crowd_mood','crowd_position','event_pause',
                'road_documents','involved_entities_other'):
        assert f'name="{key}"' in html
    for key in ('venue_context','venue_features','venue_logistics','involved_entities'):
        assert key+':{' in js
    assert 'for(const name of multiChoiceNames)values[name]=checkedChoices(name)' in js
    assert 'loadPreviousEvents()' in js


def test_older_submitted_payload_still_parses_and_exports():
    from app.main import Submission
    older=VALUES.copy()
    for key in ('org_first_name','org_last_name','venue_context','venue_features',
                'venue_logistics','event_pause','road_documents','crowd_age_profile',
                'crowd_density','crowd_mood','crowd_position','involved_entities',
                'involved_entities_other','event_duration_bracket',
                'participants_estimate_bracket'):
        older.pop(key,None)
    old_model=Submission.model_validate(older)
    assert old_model.org_contact=='Mario Rossi'
    assert not old_model.venue_features
    assert render_excel(TEMPLATE,old_model.model_dump())
