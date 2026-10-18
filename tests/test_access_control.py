"""Security and delivery regression tests. All customer data is synthetic."""
import os
import tempfile
from pathlib import Path

TEST_DIR=tempfile.mkdtemp(prefix="cri-protocol-test-")
os.environ["DATA_DIR"]=TEST_DIR
os.environ["DATABASE_URL"]="sqlite:///"+str(Path(TEST_DIR)/"test.db")
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
    client=TestClient(app)
    home=client.get("/")
    assert home.status_code==200,home.text
    assert "Accesso operatori CRI" in home.text
    assert client.get("/health").json()=={"status":"ok"}


def test_multiuser_protocol_and_internal_recipients(monkeypatch):
    admin,ah=login("admin@example.com",os.environ["ADMIN_PASSWORD"])
    for email,name in (("maria@example.com","Maria"),("luca@example.com","Luca")):
        response=admin.post("/api/users",headers=ah,json={
            "email":email,"display_name":name,"password":"Temporary-test-password-123!"})
        assert response.status_code==200,response.text
    maria,mh=login("maria@example.com","Temporary-test-password-123!")
    luca,lh=login("luca@example.com","Temporary-test-password-123!")
    created=maria.post("/api/requests",headers=mh,json={
        "customer_email":"organizzatore@example.com","event_name":"Porte Aperte",
        "event_city":"Venezia","days":14})
    assert created.status_code==200,created.text
    request_id=created.json()["id"]
    token=created.json()["url"].split("/r/")[1]
    mine=maria.get("/api/requests").json()
    assert len(mine)==1 and mine[0]["id"]==request_id
    assert mine[0]["creator_email"]=="maria@example.com"
    assert mine[0]["event_name"]=="Porte Aperte" and mine[0]["event_city"]=="Venezia"
    assert mine[0]["created_at"] and mine[0]["expires_at"]
    assert mine[0]["protocol_number"] is None
    assert luca.get("/api/requests").json()==[]
    assert luca.get(f"/api/requests/{request_id}").status_code==404
    assert luca.get(f"/api/requests/{request_id}/data").status_code==404
    assert luca.get(f"/api/requests/{request_id}/excel").status_code==404
    assert luca.post(f"/api/requests/{request_id}/archive",headers=lh).status_code==404
    assert luca.post(f"/api/requests/{request_id}/send-email",headers=lh).status_code==404
    assert admin.get("/api/requests").json()[0]["creator_email"]=="maria@example.com"
    assert maria.get("/api/users").status_code==403
    assert maria.post("/api/users",headers=mh,json={
        "email":"alice@example.com","display_name":"Alice","password":"aaaaaaaaaaaa"}).status_code==403
    assert maria.get("/api/settings/mail").status_code==403
    assert maria.post("/r/"+token,data={"org_name":"Private"}).status_code==405
    page=maria.get("/r/"+token)
    assert page.status_code==200 and 'method="post"' in page.text
    assert 'id="sendRequest" disabled' in page.text
    token_info=maria.get("/api/r/"+token).json()
    assert token_info["event_name"]=="Porte Aperte" and token_info["event_city"]=="Venezia"
    leaked_get=maria.get("/r/"+token+"?org_name=Private",follow_redirects=False)
    assert leaked_get.status_code==303 and "?org_name=" not in leaked_get.headers["location"]
    assert maria.get("/api/requests").json()[0]["status"]=="pending"

    configured=admin.put("/api/settings/mail",headers=ah,json={
        "enabled":True,"recipients":"office@example.com;admin@example.com",
        "subject":"Piano Sanitario {protocol} - {event}",
        "body":"Evento {event}: {protocol_date}"})
    assert configured.status_code==200,configured.text
    captured=[]
    class FakeSMTP:
        def __init__(self,*args,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def starttls(self,**kwargs):pass
        def login(self,*args):pass
        def send_message(self,message):captured.append(message)
    monkeypatch.setattr(backend.smtplib,"SMTP",FakeSMTP)
    monkeypatch.setattr(backend,"render_excel",lambda template,data:b"TEST FILE CONTENT")
    monkeypatch.setenv("SMTP_HOST","smtp.example.com")
    monkeypatch.setenv("SMTP_FROM","sender@example.com")
    monkeypatch.setenv("SMTP_USER","sender@example.com")
    data={
        "org_name":"Ente esempio","org_contact":"Referente Esempio",
        "org_address":"Via Roma 10 Venezia","org_phone":"0410000000",
        "org_email":"organizzatore@example.com","event_name":"Porte Aperte",
        "event_city":"Venezia","event_dates":"2026-11-24",
        "event_time":"2026-11-24 09:00-18:00",
        "event_slots":[{"date":"2026-11-24","start":"09:00","end":"18:00"}],
        "event_place":"Via Roma 10, Venezia",
        "event_description":"Descrizione di evento dimostrativo",
        "reference_name":"Mario Esempio","reference_phone":"0410000000",
        "privacy_ack":True,"declaration":True
    }
    submitted=maria.put("/api/r/"+token,json=data)
    assert submitted.status_code==200,submitted.text
    receipt=submitted.json()
    assert receipt["status"]=="submitted" and receipt["mail_status"]=="sent"
    assert receipt["protocol_number"]==f"CRI-VE/{receipt['protocol_at'][:4]}/{request_id:06d}"
    assert receipt["protocol_at"]
    assert len(captured)==1
    recipients={s.strip() for s in captured[0]["To"].split(",")}
    assert recipients=={"admin@example.com","office@example.com","maria@example.com"}
    assert "organizzatore@example.com" not in recipients
    assert receipt["protocol_number"] in captured[0]["Subject"]
    assert receipt["protocol_number"] in captured[0].get_content()
    details=maria.get(f"/api/requests/{request_id}").json()
    assert details["protocol_number"]==receipt["protocol_number"]
    assert details["protocol_at"]==receipt["protocol_at"]
    assert maria.get("/api/requests?view=compiled").json()[0]["protocol_number"]==receipt["protocol_number"]
    assert maria.put("/api/r/"+token,json=data).status_code==410

    archived=maria.post(f"/api/requests/{request_id}/archive",headers=mh)
    assert archived.status_code==200
    assert maria.get("/r/"+token).status_code==410
    assert maria.post(f"/api/requests/{request_id}/archive?archived=false",headers=mh).status_code==200
    assert maria.get("/r/"+token).status_code==410

    users=admin.get("/api/users").json()
    maria_id=next(u["id"] for u in users if u["email"]=="maria@example.com")
    reset=admin.put(f"/api/users/{maria_id}/password",headers=ah,json={
        "password":"New-temporary-test-password-456!"})
    assert reset.status_code==200
    assert maria.get("/api/session").status_code==401
    relogin,_=login("maria@example.com","New-temporary-test-password-456!")
    assert relogin.get("/api/session").status_code==200
    new_email=admin.put(f"/api/users/{maria_id}/email",headers=ah,json={"email":"maria2@example.com"})
    assert new_email.status_code==200
    assert relogin.get("/api/session").status_code==401
    relogin,_=login("maria2@example.com","New-temporary-test-password-456!")
    assert admin.put(f"/api/users/{maria_id}/status",headers=ah,json={"active":False}).status_code==200
    assert relogin.get("/api/session").status_code==401
