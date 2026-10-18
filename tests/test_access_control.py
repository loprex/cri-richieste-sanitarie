"""Security, activation and Excel-filename tests. All accounts are synthetic."""
import os
import re
import tempfile
from pathlib import Path

ROOT=tempfile.mkdtemp(prefix="cri-test-")
os.environ["DATA_DIR"]=ROOT
os.environ["DATABASE_URL"]="sqlite:///"+str(Path(ROOT)/"test.db")
os.environ["ADMIN_PASSWORD"]="sample-admin-password-for-tests-only-1234"
os.environ["SESSION_SECRET"]="sample-test-secret-key-not-for-production-0123456789"
os.environ["CRI_ADMIN_EMAIL"]="admin@example.com"
os.environ["COOKIE_SECURE"]="false"
os.environ.pop("SMTP_HOST",None)

from fastapi.testclient import TestClient
from app.main import app
import app.main as backend

def login(email,password):
    client=TestClient(app)
    response=client.post("/api/login",json={"email":email,"password":password})
    assert response.status_code==200,response.text
    return client,{"x-cri-csrf":response.json()["csrf"]}

def test_public_routes_present():
    c=TestClient(app)
    assert c.get("/").status_code==200
    assert c.get("/health").json()=={"status":"ok"}

def test_single_prior_event_selection_markup():
    # Client may select fields freely, but never combine two old events.
    from pathlib import Path
    form_js=(Path(backend.__file__).parent/"static"/"form.js").read_text()
    form_html=(Path(backend.__file__).parent/"static"/"form.html").read_text()
    assert "input.type='radio';input.name='previousEventChoice'" in form_js
    assert "document.querySelector('input[name=\"previousEventChoice\"]:checked')" in form_js
    assert "for(const id of ids)" not in form_js
    assert "input.type='checkbox';input.className='reuseField'" in form_js
    assert "Seleziona un solo evento" in form_html

def test_user_activation_and_case_lifecycle(monkeypatch):
    sent=[]
    class FakeSMTP:
        def __init__(self,*args,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def starttls(self,**kwargs):pass
        def login(self,*args):pass
        def send_message(self,mail):sent.append(mail)
    monkeypatch.setattr(backend.smtplib,"SMTP",FakeSMTP)
    monkeypatch.setattr(backend,"render_excel",lambda template,data:b"FAKE XLSX")
    monkeypatch.setenv("SMTP_HOST","smtp.example.com")
    monkeypatch.setenv("SMTP_FROM","sender@example.com")
    monkeypatch.setenv("SMTP_USER","sender@example.com")
    admin,ah=login("admin@example.com",os.environ["ADMIN_PASSWORD"])
    second_admin=next(u for u in admin.get("/api/users").json()
        if u["email"]=="amministrazione@crivenezia.it")
    assert second_admin["role"]=="admin"
    assert second_admin["password_setup_required"] is True
    # Designated admin has no initial password until activated via its own mailbox.
    assert TestClient(app).post("/api/login",json={
      "email":"amministrazione@crivenezia.it","password":"guess-password"}).status_code==401
    # TEST must never contact the designated administration mailbox, even for
    # password setup or SMTP diagnosis; no token or current password is revoked.
    assert admin.post(f"/api/users/{second_admin['id']}/send-setup",
        headers=ah,json={}).status_code==409
    assert backend.send_password_setup('amministrazione@crivenezia.it','Admin','https://example.com/activate/mock')=='suppressed_until_production'
    assert backend.send_invitation(1,'amministrazione@crivenezia.it','https://example.com/r/mock',14)=='suppressed_until_production'
    assert len(sent)==0
    # Prove that the full admin role continues to work AFTER activation. All
    # email in this test uses FakeSMTP; production opt-in is momentary.
    monkeypatch.setenv("CRI_DEPLOYMENT_ENV","production")
    monkeypatch.setenv("CRI_ENABLE_ADMINISTRATION_EMAIL","true")
    activation=admin.post(f"/api/users/{second_admin['id']}/send-setup",headers=ah,json={})
    assert activation.status_code==200 and activation.json()["activation_status"]=="sent"
    admin_setup_token=re.search(r"/activate/([A-Za-z0-9_-]{35,128})",sent[-1].get_content()).group(1)
    assert TestClient(app).post("/api/activate/"+admin_setup_token,
        json={"password":"Administration-password-2026!"}).status_code==200
    monkeypatch.setenv("CRI_DEPLOYMENT_ENV","test")
    monkeypatch.setenv("CRI_ENABLE_ADMINISTRATION_EMAIL","false")
    second_admin_client,second_admin_headers=login(
        "amministrazione@crivenezia.it","Administration-password-2026!")
    assert second_admin_client.get("/api/users").status_code==200
    assert second_admin_client.get("/api/settings/mail").status_code==200
    for email,name in (("maria@example.com","Maria"),("luca@example.com","Luca")):
        created=admin.post("/api/users",headers=ah,json={"email":email,"display_name":name})
        assert created.status_code==200,created.text
        assert created.json()["activation_status"]=="sent"
        assert TestClient(app).post("/api/login",json={"email":email,"password":"Any Password"}).status_code==401
        mail=sent[-1]
        match=re.search(r"/activate/([A-Za-z0-9_-]{35,128})",mail.get_content())
        assert match
        token=match.group(1)
        user_page=TestClient(app).get("/activate/"+token)
        assert user_page.status_code==200 and "Imposta la tua password" in user_page.text
        first=TestClient(app).post("/api/activate/"+token,json={"password":"First-personal-password-123!"})
        assert first.status_code==200,first.text
        assert TestClient(app).post("/api/activate/"+token,json={"password":"Second-password-123!"}).status_code==410
        assert TestClient(app).get("/activate/"+token).status_code==410
    maria,mh=login("maria@example.com","First-personal-password-123!")
    luca,lh=login("luca@example.com","First-personal-password-123!")
    made=maria.post("/api/requests",headers=mh,json={
       "customer_email":"organizzatore@example.com","event_name":"Porte Aperte",
       "event_city":"Venezia","days":14})
    assert made.status_code==200,made.text
    req_id=made.json()["id"]
    token=made.json()["url"].split("/r/")[1]
    row=maria.get("/api/requests").json()[0]
    assert row["created_at"] and row["expires_at"] and row["protocol_number"] is None
    assert row["creator_email"]=="maria@example.com"
    # An administrator sees all operators' requests, unlike ordinary users.
    assert second_admin_client.get("/api/requests").json()[0]["id"]==req_id
    assert second_admin_client.get(f"/api/requests/{req_id}").status_code==200
    assert row["event_name"]=="Porte Aperte"
    assert luca.get("/api/requests").json()==[]
    assert luca.get(f"/api/requests/{req_id}").status_code==404
    assert luca.get(f"/api/requests/{req_id}/excel").status_code==404
    assert luca.post(f"/api/requests/{req_id}/archive",headers=lh).status_code==404
    assert maria.get("/api/users").status_code==403
    assert maria.get("/api/r/"+token).json()["event_city"]=="Venezia"
    assert maria.get("/api/r/"+token+"/previous-events").json()==[]
    assert maria.post("/r/"+token,data={"org_name":"Test"}).status_code==405
    assert maria.get("/r/"+token+"?org_name=Test",follow_redirects=False).status_code==303

    class FakeResponse:
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):
            return b'{"features":[{"properties":{"street":"Via Roma","housenumber":"10","postcode":"30100","city":"Venezia","state":"Veneto","countrycode":"IT"}}]}'
    monkeypatch.setattr(backend,"urlopen",lambda *args,**kwargs:FakeResponse())
    matches=maria.get(f"/api/r/{token}/address-suggestions?q=Via%20Roma").json()
    assert matches["suggestions"]==["Via Roma 10, 30100 Venezia, Veneto"]
    assert maria.get(f"/api/r/{token}/address-suggestions?q=AB").status_code==422
    # Photon errors are classified without exposing queries or token values.
    def reject_with_rate_limit(*args,**kwargs):
        raise backend.HTTPError('https://photon.komoot.io/api',429,'Too Many Requests',{},None)
    monkeypatch.setattr(backend,'urlopen',reject_with_rate_limit)
    overloaded=maria.get(f"/api/r/{token}/address-suggestions?q=Vicolo%20Nuovo")
    assert overloaded.status_code==200
    assert overloaded.json()['available'] is False
    assert overloaded.json()['reason']=='rate_limited'
    # Cached successful queries do not repeatedly contact the public demo.
    cached=maria.get(f"/api/r/{token}/address-suggestions?q=Via%20Roma")
    assert cached.status_code==200 and cached.json()['available'] is True

    settings=admin.put("/api/settings/mail",headers=ah,json={
       "enabled":True,"recipients":"office@example.com;admin@example.com;amministrazione@crivenezia.it",
       "subject":"Piano Sanitario {protocol} - {event}","body":"Evento {event} {protocol_date}"})
    assert settings.status_code==200,settings.text
    assert admin.get("/api/settings/mail").json()["administration_mail_paused"] is True
    blocked=admin.post("/api/settings/mail/test",headers=ah,json={
        "to":"amministrazione@crivenezia.it"})
    assert blocked.status_code==409
    assert not any(mail["To"]=="amministrazione@crivenezia.it" for mail in sent)
    test_email=admin.post("/api/settings/mail/test",headers=ah,json={
       "to":"office@example.com"})
    assert test_email.status_code==200,test_email.text
    assert test_email.json()["status"]=="accepted_by_smtp"
    assert sent[-1]["To"]=="office@example.com"
    forbidden=admin.post("/api/settings/mail/test",headers=ah,json={
       "to":"unknown@example.com"})
    assert forbidden.status_code==403
    data={
       "org_name":"Ente esempio","org_contact":"Referente Esempio",
       "org_address":"Via Roma 10 Venezia","org_phone":"0410000000",
       "org_vat":"00000000000","org_sdi":"ABCDEFG","org_pec":"protocollo@example.com",
       "org_email":"organizzatore@example.com","event_name":"Porte Aperte",
       "event_city":"Venezia","event_dates":"2026-11-24",
       "event_time":"2026-11-24 09:00-18:00",
       "event_slots":[{"date":"2026-11-24","start":"09:00","end":"18:00"}],
       "event_place":"Via Roma 10, Venezia",
       "event_description":"Descrizione evento dimostrativo",
       "reference_name":"Mario Esempio","reference_phone":"0410000000",
       "participants_athletes":30,"participants_public":300,
       "privacy_ack":True,"declaration":True
    }
    # Autosave is not a trigger. Finalization fires exactly one notification.
    plans_before=len([mail for mail in sent if mail.get_content_maintype()=="multipart"])
    draft_reply=maria.put("/api/r/"+token+"?draft=true",json=data)
    assert draft_reply.status_code==200,draft_reply.text
    assert draft_reply.json()["status"]=="draft"
    assert len([mail for mail in sent if mail.get_content_maintype()=="multipart"])==plans_before
    reply=maria.put("/api/r/"+token,json=data)
    assert reply.status_code==200,reply.text
    receipt=reply.json()
    assert receipt["mail_status"]=="sent" and receipt["status"]=="submitted"
    assert receipt["protocol_number"]==f"CRI-VE/{receipt['protocol_at'][:4]}/{req_id:06d}"
    saved=maria.get(f"/api/requests/{req_id}").json()
    filename=backend.plan_filename(saved)
    assert filename.startswith("piano_sanitario_bozza_")
    assert receipt["protocol_at"][:10].replace("-","") in filename
    assert receipt["protocol_number"].replace("/","-") in filename
    downloads=maria.get(f"/api/requests/{req_id}/excel")
    assert downloads.status_code==200
    assert filename in downloads.headers["Content-Disposition"]
    plan_mails=[m for m in sent if m.get_content_maintype()=="multipart"]
    assert len(plan_mails)==1
    email=plan_mails[0]
    rec={x.strip() for x in email["To"].split(",")}
    assert rec=={"admin@example.com","office@example.com","maria@example.com"}
    assert "amministrazione@crivenezia.it" not in rec
    assert "organizzatore@example.com" not in rec
    assert filename in [p.get_filename() for p in email.iter_attachments()]
    deep_link="/?request="+str(req_id)
    assert deep_link in email.get_body(preferencelist=('plain',)).get_content()
    assert deep_link in email.get_body(preferencelist=('html',)).get_content()
    assert "Piano Sanitario Excel" in email.get_body(preferencelist=('html',)).get_content()
    # Delivery to internal recipients must not include the original organizer.
    assert "organizzatore@example.com" not in rec
    assert maria.put("/api/r/"+token,json=data).status_code==410
    assert len([mail for mail in sent if mail.get_content_maintype()=="multipart"])==1

    # New-event vs copy-previous choice: only the same recipient email and
    # same CRI creator may see completed past event fields (archived or not).
    second=maria.post("/api/requests",headers=mh,json={
        "customer_email":"ORGANIZZATORE@example.com","event_name":"Maratona dei Dogi",
        "event_city":"Venezia","days":14})
    assert second.status_code==200,second.text
    second_token=second.json()["url"].split("/r/")[1]
    histories=maria.get("/api/r/"+second_token+"/previous-events")
    assert histories.status_code==200,histories.text
    assert histories.headers["Cache-Control"]=="no-store"
    old=histories.json()
    assert len(old)==1
    assert old[0]["id"]==req_id and old[0]["name"]=="Porte Aperte"
    assert old[0]["data"]["event_place"]=="Via Roma 10, Venezia"
    assert old[0]["data"]["participants_athletes"]==30
    assert old[0]["data"]["event_city"]=="Venezia"
    assert "event_dates" not in old[0]["data"]
    assert "event_slots" not in old[0]["data"]
    assert old[0]["data"]["org_name"]=="Ente esempio"
    assert old[0]["data"]["org_contact"]=="Referente Esempio"
    assert old[0]["data"]["org_address"]=="Via Roma 10 Venezia"
    assert old[0]["data"]["org_phone"]=="0410000000"
    assert old[0]["data"]["org_vat"]=="00000000000"
    assert old[0]["data"]["org_sdi"]=="ABCDEFG"
    assert old[0]["data"]["org_pec"]=="protocollo@example.com"
    # Invitation email stays fixed; previous org email is never copied.
    assert "org_email" not in old[0]["data"]
    assert "protocol_number" not in old[0]["data"]
    other=maria.post("/api/requests",headers=mh,json={
        "customer_email":"another@example.com","event_name":"Evento diverso",
        "event_city":"Padova","days":14})
    assert other.status_code==200
    other_token=other.json()["url"].split("/r/")[1]
    assert maria.get("/api/r/"+other_token+"/previous-events").json()==[]
    other_owner=luca.post("/api/requests",headers=lh,json={
        "customer_email":"organizzatore@example.com","event_name":"Evento riservato",
        "event_city":"Venezia","days":14})
    assert other_owner.status_code==200
    other_owner_token=other_owner.json()["url"].split("/r/")[1]
    assert luca.get("/api/r/"+other_owner_token+"/previous-events").json()==[]

    assert maria.post(f"/api/requests/{req_id}/archive",headers=mh).status_code==200
    assert maria.get("/r/"+token).status_code==410
    assert len(maria.get("/api/r/"+second_token+"/previous-events").json())==1
    assert maria.post(f"/api/requests/{req_id}/archive?archived=false",headers=mh).status_code==200
    assert maria.get("/r/"+token).status_code==410

    maria_id=next(x["id"] for x in admin.get("/api/users").json() if x["email"]=="maria@example.com")
    reset=admin.post(f"/api/users/{maria_id}/send-setup",headers=ah,json={})
    assert reset.status_code==200 and reset.json()["activation_status"]=="sent"
    assert maria.get("/api/session").status_code==401
    reset_token=re.search(r"/activate/([A-Za-z0-9_-]{35,128})",sent[-1].get_content()).group(1)
    assert TestClient(app).post("/api/activate/"+reset_token,json={"password":"Changed-personal-password-456!"}).status_code==200
    new_login,_=login("maria@example.com","Changed-personal-password-456!")
    assert admin.put(f"/api/users/{maria_id}/status",headers=ah,json={"active":False}).status_code==200
    assert new_login.get("/api/session").status_code==401
