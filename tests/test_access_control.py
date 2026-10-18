"""Non-production regression tests using a disposable SQLite DB and synthetic records."""
import os
import tempfile
from pathlib import Path

TEST_DIR=tempfile.mkdtemp(prefix="cri-test-")
os.environ["DATA_DIR"]=TEST_DIR
os.environ["DATABASE_URL"]="sqlite:///"+str(Path(TEST_DIR)/"test.db")
os.environ["ADMIN_PASSWORD"]="sample-admin-password-for-tests-only-1234"
os.environ["SESSION_SECRET"]="sample-test-secret-key-not-for-production-0123456789"
os.environ["COOKIE_SECURE"]="false"
os.environ.pop("SMTP_HOST",None)

from fastapi.testclient import TestClient
from app.main import app


def login(username,password):
    client=TestClient(app)
    response=client.post("/api/login",json={"username":username,"password":password})
    assert response.status_code==200,response.text
    return client,{"x-cri-csrf":response.json()["csrf"]}

def test_isolation_reset_dates_and_archiving():
    admin,ah=login("admin",os.environ["ADMIN_PASSWORD"])
    for name in ("maria","luca"):
        response=admin.post("/api/users",headers=ah,json={
            "username":name,"display_name":name.title(),"password":"Temporary-test-password-123!"})
        assert response.status_code==200,response.text
    maria,mh=login("maria","Temporary-test-password-123!")
    luca,lh=login("luca","Temporary-test-password-123!")
    created=maria.post("/api/requests",headers=mh,json={"customer_email":"event@example.test","days":14})
    assert created.status_code==200,created.text
    request_id=created.json()["id"]
    token_url=created.json()["url"]
    mine=maria.get("/api/requests").json()
    assert len(mine)==1 and mine[0]["id"]==request_id
    assert mine[0]["creator_username"]=="maria" and mine[0]["created_at"] and mine[0]["expires_at"]
    assert luca.get("/api/requests").json()==[]
    assert luca.get(f"/api/requests/{request_id}").status_code==404
    assert luca.get(f"/api/requests/{request_id}/data").status_code==404
    assert luca.get(f"/api/requests/{request_id}/excel").status_code==404
    assert luca.post(f"/api/requests/{request_id}/archive",headers=lh).status_code==404
    assert luca.post(f"/api/requests/{request_id}/send-email",headers=lh).status_code==404
    assert admin.get("/api/requests").json()[0]["creator_username"]=="maria"
    assert maria.get("/api/users").status_code==403
    assert maria.post("/api/users",headers=mh,json={"username":"alice","display_name":"Alice","password":"aaaaaaaaaaaa"}).status_code==403
    assert maria.get("/api/settings/mail").status_code==403
    # Without JavaScript, native POST must not leak submitted fields into a URL.
    assert maria.post("/r/"+token_url.split("/r/")[1],data={"org_name":"Sample"}).status_code==405
    page=maria.get("/r/"+token_url.split("/r/")[1])
    assert page.status_code==200 and 'method="post"' in page.text and 'id="sendRequest" disabled' in page.text
    # Old browsers submitting GET query parameters must never save customer PII.
    leaked_get=maria.get("/r/"+token_url.split("/r/")[1]+"?org_name=Test%20Private",follow_redirects=False)
    assert leaked_get.status_code==303
    assert "?org_name=" not in leaked_get.headers["location"]
    assert maria.get('/api/requests').json()[0]['status']=='pending'

    # Archiving permanently revokes the bearer link, including after restore.
    archived=maria.post(f"/api/requests/{request_id}/archive",headers=mh)
    assert archived.status_code==200
    assert maria.get("/r/"+token_url.split("/r/")[1]).status_code==410
    assert maria.post(f"/api/requests/{request_id}/archive?archived=false",headers=mh).status_code==200
    assert maria.get("/r/"+token_url.split("/r/")[1]).status_code==410
    users=admin.get("/api/users").json()
    maria_id=next(u["id"] for u in users if u["username"]=="maria")
    reset=admin.put(f"/api/users/{maria_id}/password",headers=ah,json={"password":"New-temporary-test-password-456!"})
    assert reset.status_code==200
    assert maria.get("/api/session").status_code==401
    relogin,_=login("maria","New-temporary-test-password-456!")
    assert relogin.get("/api/session").status_code==200
    assert admin.put(f"/api/users/{maria_id}/status",headers=ah,json={"active":False}).status_code==200
    assert relogin.get("/api/session").status_code==401
