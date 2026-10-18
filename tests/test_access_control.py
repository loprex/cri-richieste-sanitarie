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
    assert "previousYearFilter" in form_html
    assert "renderPreviousEvents()" in form_js
    assert "previous-event-card" in form_js
    assert "input.name='previousEventChoice'" in form_js

def test_previous_event_year_filter_metadata():
    # Date of event takes precedence over submission year; old records use
    # their completion date when the event date was not stored.
    assert backend.previous_event_years({
      "event_slots":[{"date":"2027-05-01"},{"date":"2028-01-03"}]},
      "2026-10-18T14:00:00+02:00")==([2028,2027],"event")
    assert backend.previous_event_years({
      "event_dates":"18/10/2025, 19/10/2025"},
      "2026-10-18T14:00:00+02:00")==([2025],"event")
    assert backend.previous_event_years({
      "event_dates":"2029-03-15"},
      "2026-10-18T14:00:00+02:00")==([2029],"event")
    assert backend.previous_event_years({},
      "2024-01-01T09:00:00+01:00")==([2024],"submission")

def test_login_three_failures_manual_lock_and_password_recovery(monkeypatch):
    """Test DB-persistent lock, single-use recovery and admin-only manual unlocking."""
    # The production owner mailbox differs from synthetic test fixtures.
    monkeypatch.setattr(backend,'OWNER_DELETE_EMAIL','admin@example.com')
    import uuid
    backend._LOGIN_ATTEMPTS.clear()
    backend._RESET_REQUESTS.clear()
    delivered=[]
    class SMTP:
        def __init__(self,*a,**k):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def starttls(self,**k):pass
        def login(self,*a):pass
        def send_message(self,email):delivered.append(email)
    monkeypatch.setenv("SMTP_HOST","smtp.example.com")
    monkeypatch.setenv("SMTP_FROM","sender@example.com")
    monkeypatch.setenv("SMTP_USER","sender@example.com")
    monkeypatch.setenv("CRI_DEPLOYMENT_ENV","test")
    monkeypatch.setenv("CRI_ENABLE_ADMINISTRATION_EMAIL","false")
    monkeypatch.setattr(backend.smtplib,"SMTP",SMTP)
    email="lock-"+uuid.uuid4().hex[:10]+"@example.com"
    old_password="Correct-password-2026!"
    new_password="Recovered-password-2026!"
    with backend.db() as c:
        uid=c.execute(backend.text("""INSERT INTO app_users
           (username,email,display_name,password_hash,role,active,
            auth_version,created_at)
           VALUES(:username,:email,'Utente bloccabile',:password,'operator',TRUE,:version,:at)
           RETURNING id"""),
           {'username':'user-'+uuid.uuid4().hex[:16],'email':email,
            'password':backend.password_hash(old_password),
            'version':uuid.uuid4().hex,'at':backend.iso()}).scalar_one()
    admin,ah=login("admin@example.com",os.environ["ADMIN_PASSWORD"])
    c=TestClient(app)
    for expected in (401,401,423):
        attempt=c.post("/api/login",json={"email":email,"password":"Wrong-password-000"})
        assert attempt.status_code==expected,attempt.text
    with backend.db() as tx:
        row=backend.fetchone(tx,"SELECT failed_login_attempts,auto_locked_at FROM app_users WHERE id=:id",{"id":uid})
    assert row["failed_login_attempts"]==3 and row["auto_locked_at"]
    assert c.post("/api/login",json={"email":email,"password":old_password}).status_code==423
    users=admin.get("/api/users").json()
    found=next(item for item in users if item["id"]==uid)
    assert found["auto_locked_at"] and found["failed_login_attempts"]==3

    # Always return the same response for valid, unknown or suppressed addresses.
    hidden=c.post("/api/password/forgot",json={"email":"nobody-registered@example.com"})
    issued=c.post("/api/password/forgot",json={"email":email})
    suppressed=c.post("/api/password/forgot",json={"email":"amministrazione@crivenezia.it"})
    assert hidden.status_code==issued.status_code==suppressed.status_code==200
    assert hidden.json()==issued.json()==suppressed.json()
    assert len(delivered)==1 and delivered[0]["To"]==email
    assert delivered[0]["Subject"]=="CRI Venezia - Recupero password"
    token=re.search(r"/reset/([A-Za-z0-9_-]{35,128})",delivered[0].get_content()).group(1)
    assert c.get("/reset/"+token).status_code==200
    reset=c.post("/api/password/reset/"+token,json={"password":new_password})
    assert reset.status_code==200,reset.text
    assert c.post("/api/password/reset/"+token,json={"password":new_password}).status_code==410
    assert c.get("/reset/"+token).status_code==410
    assert c.post("/api/login",json={"email":email,"password":new_password}).status_code==200
    with backend.db() as tx:
        row=backend.fetchone(tx,"SELECT failed_login_attempts,auto_locked_at FROM app_users WHERE id=:id",{"id":uid})
    assert row["failed_login_attempts"]==0 and row["auto_locked_at"] is None

    # Auto-block can also be lifted directly by another administrator.
    for expected in (401,401,423):
        attempt=c.post("/api/login",json={"email":email,"password":"Wrong-again-000"})
        assert attempt.status_code==expected,attempt.text
    assert c.post(f"/api/users/{uid}/unlock",json={}).status_code==401
    assert admin.post(f"/api/users/{uid}/unlock",headers=ah,json={}).status_code==200
    signed,_=login(email,new_password)
    assert signed.get("/api/session").status_code==200
    assert admin.put(f"/api/users/{uid}/status",headers=ah,json={"active":False}).status_code==200
    assert signed.get("/api/session").status_code==401
    assert c.post("/api/login",json={"email":email,"password":new_password}).status_code==423
    assert admin.post(f"/api/users/{uid}/unlock",headers=ah,json={}).status_code==409
    # Manual block cannot be bypassed with a self-service reset request.
    mails_before=len(delivered)
    assert c.post("/api/password/forgot",json={"email":email}).status_code==200
    assert len(delivered)==mails_before
    assert admin.put(f"/api/users/{uid}/status",headers=ah,json={"active":True}).status_code==200
    assert c.post("/api/login",json={"email":email,"password":new_password}).status_code==200
    # A currently signed-in administrator cannot block their own account.
    assert admin.put(f"/api/users/{ah_user_id(admin)}/status",headers=ah,json={"active":False}).status_code==409


def ah_user_id(admin):
    return admin.get("/api/session").json()["user_id"]


def test_user_activation_and_case_lifecycle(monkeypatch):
    monkeypatch.setattr(backend,'OWNER_DELETE_EMAIL','admin@example.com')
    monkeypatch.setattr(backend,"now_venice",lambda:"2026-10-18T19:00:00+02:00")
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
    # Administrators retain sanitary-request and SMTP-setting privileges,
    # but cannot enumerate or change users; only the Lopresti bootstrap owner may.
    secondary_session=second_admin_client.get("/api/session").json()
    assert secondary_session["is_admin"] is True
    assert secondary_session["can_delete_accounts"] is False
    assert second_admin_client.get("/api/users").status_code==403
    assert second_admin_client.get("/api/settings/mail").status_code==200
    assert second_admin_client.post("/api/users",headers=second_admin_headers,
        json={"email":"forbidden@example.com","display_name":"Non consentito"}).status_code==403
    assert second_admin_client.put(f"/api/users/{second_admin['id']}/email",
        headers=second_admin_headers,json={"email":"forbidden@example.com"}).status_code==403
    assert second_admin_client.put(f"/api/users/{second_admin['id']}/status",
        headers=second_admin_headers,json={"active":False}).status_code==403
    assert second_admin_client.post(f"/api/users/{second_admin['id']}/unlock",
        headers=second_admin_headers,json={}).status_code==403
    assert second_admin_client.post(f"/api/users/{second_admin['id']}/send-setup",
        headers=second_admin_headers,json={}).status_code==403
    assert second_admin_client.request("DELETE",f"/api/users/{second_admin['id']}",
        headers=second_admin_headers,json={
           "password":"Administration-password-2026!",
           "confirm_email":"amministrazione@crivenezia.it",
           "confirmation":"ELIMINA"}).status_code==403
    assert admin.get("/api/session").json()["can_delete_accounts"] is True
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
    requested_urls=[]
    def mock_geocoder(request,timeout):
        requested_urls.append(request.full_url)
        return FakeResponse()
    monkeypatch.setattr(backend,"urlopen",mock_geocoder)
    matches=maria.get(f"/api/r/{token}/address-suggestions?q=Via%20Roma").json()
    assert matches["suggestions"]==["Via Roma 10, 30100 Venezia, Veneto"]
    from urllib.parse import urlsplit,parse_qs
    query_params=parse_qs(urlsplit(requested_urls[0]).query)
    assert query_params["q"]==["Via Roma"]
    assert query_params["limit"]==["8"]
    assert "lang" not in query_params  # Some Photon demo deployments reject lang=it with HTTP 400.
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
    assert receipt["protocol_number"]=="CRI-VE/2026/000001"
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
    assert old[0]["years"]==[2026]
    assert old[0]["year_basis"]=="event"
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

    # Year-based protocol numbers start again at 000001 on 1 January,
    # regardless of the global request ID. Existing 2026 numbers are immutable.
    monkeypatch.setattr(backend,"now_venice",lambda:"2027-01-01T00:02:00+01:00")
    for n in (1,2):
        event=admin.post("/api/requests",headers=ah,json={
          "customer_email":"annual@example.com",
          "event_name":f"Manifestazione 2027 n. {n}",
          "event_city":"Venezia","days":14})
        assert event.status_code==200,event.text
        annual_token=event.json()["url"].split("/r/")[1]
        annual_data=dict(data,event_name=f"Manifestazione 2027 n. {n}",
          org_email="annual@example.com",event_dates="2027-06-20",
          event_time="2027-06-20 09:00-18:00",
          event_slots=[{"date":"2027-06-20","start":"09:00","end":"18:00"}])
        submitted=admin.put("/api/r/"+annual_token,json=annual_data)
        assert submitted.status_code==200,submitted.text
        assert submitted.json()["protocol_number"]==f"CRI-VE/2027/{n:06d}"
        assert submitted.json()["protocol_at"].startswith("2027-01-01")
    assert admin.get(f"/api/requests/{req_id}").json()["protocol_number"]=="CRI-VE/2026/000001"

    # The allocator also resumes safely from protocols created by the old
    # ID-based scheme in a year with no counter yet.
    with backend.db() as c:
        c.execute(backend.text("""INSERT INTO requests
          (token_hash,customer_email,created_at,expires_at,status,payload,
           protocol_number,protocol_at) VALUES
          (:hash,'legacy@example.com',:at,:at,'submitted','{}',
           'CRI-VE/2038/000042',:at)"""),
          {"hash":backend.digest("legacy-2038"),"at":"2038-01-02T09:00:00+01:00"})
        assert backend.allocate_annual_protocol(c,2038)=="CRI-VE/2038/000043"
        assert backend.allocate_annual_protocol(c,2038)=="CRI-VE/2038/000044"

