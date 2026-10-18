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
    assert row["event_name"]=="Porte Aperte"
    assert luca.get("/api/requests").json()==[]
    assert luca.get(f"/api/requests/{req_id}").status_code==404
    assert luca.get(f"/api/requests/{req_id}/excel").status_code==404
    assert luca.post(f"/api/requests/{req_id}/archive",headers=lh).status_code==404
    assert maria.get("/api/users").status_code==403
    assert maria.get("/api/r/"+token).json()["event_city"]=="Venezia"
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

    settings=admin.put("/api/settings/mail",headers=ah,json={
       "enabled":True,"recipients":"office@example.com;admin@example.com",
       "subject":"Piano Sanitario {protocol} - {event}","body":"Evento {event} {protocol_date}"})
    assert settings.status_code==200,settings.text
    data={
       "org_name":"Ente esempio","org_contact":"Referente Esempio",
       "org_address":"Via Roma 10 Venezia","org_phone":"0410000000",
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
    assert "organizzatore@example.com" not in rec
    assert filename in [p.get_filename() for p in email.iter_attachments()]
    assert maria.put("/api/r/"+token,json=data).status_code==410
    assert maria.post(f"/api/requests/{req_id}/archive",headers=mh).status_code==200
    assert maria.get("/r/"+token).status_code==410
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
