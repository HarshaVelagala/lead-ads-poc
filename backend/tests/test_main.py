import hashlib
import hmac

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect

from app import database as database_module
from app.database import Base, get_db
from app.main import app
from app.models.lead import Lead
from app.schemas.lead import LeadCreate
from app.services import auth as auth_service
from app.services import meta_service


@pytest.fixture
def client(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        database = TestingSession()
        try:
            yield database
        finally:
            database.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("app.main.initialize_database", lambda: None)
    monkeypatch.setattr(meta_service.config, "META_VERIFY_TOKEN", "verify-me")
    monkeypatch.setattr(meta_service.config, "META_APP_SECRET", "app-secret")
    monkeypatch.setattr(auth_service.config, "ADMIN_EMAIL", "owner@example.com")
    monkeypatch.setattr(auth_service.config, "ADMIN_PASSWORD_HASH", auth_service.password_hasher.hash("owner-password"))
    monkeypatch.setattr(auth_service.config, "JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-bytes-long")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture
def auth_token(client):
    response = client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "owner-password"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def websocket_ticket(client, auth_token):
    response = client.post(
        "/auth/ws-ticket",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_login_rejects_invalid_credentials(client):
    response = client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_cors_does_not_allow_arbitrary_origins(client):
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_authentication_fails_closed_when_not_configured(client, monkeypatch):
    monkeypatch.setattr(auth_service.config, "ADMIN_PASSWORD_HASH", "")
    response = client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "owner-password"},
    )
    assert response.status_code == 503


def test_health_and_lead_crud(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/leads").status_code == 401
    assert client.get("/leads", headers=headers).status_code == 200
    assert client.post("/auth/ws-ticket").status_code == 401
    created = client.post(
        "/leads",
        json={"meta_lead_id": "meta-001", "name": "Test Lead", "email": "test@example.com", "phone": "123"},
        headers=headers,
    )
    assert created.status_code == 201
    lead = created.json()
    assert lead["meta_lead_id"] == "meta-001"
    assert lead["fullName"] == "Test Lead"
    assert lead["mobile_id"] == "meta-001"
    assert client.get("/leads", headers=headers).json()[0]["email"] == "test@example.com"
    assert client.get(f"/leads/{lead['id']}", headers=headers).json()["name"] == "Test Lead"
    assert client.get("/leads/999", headers=headers).status_code == 404


def test_meta_webhook_verification(client):
    response = client.get(
        "/webhook/meta",
        params={"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "12345"},
    )
    assert response.status_code == 200
    assert response.text == "12345"
    assert client.get("/webhook/meta", params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "1"}).status_code == 403


def test_duplicate_meta_lead_is_not_inserted_twice(client, auth_token):
    payload = {"meta_lead_id": "duplicate-1", "name": "Same Lead"}
    headers = {"Authorization": f"Bearer {auth_token}"}
    first = client.post("/leads", json=payload, headers=headers)
    second = client.post("/leads", json=payload, headers=headers)
    assert first.status_code == second.status_code == 201
    assert len(client.get("/leads", headers=headers).json()) == 1


def test_websocket_broadcasts_created_lead(client, auth_token, websocket_ticket):
    headers = {"Authorization": f"Bearer {auth_token}"}
    with client.websocket_connect(f"/ws/leads?ticket={websocket_ticket}") as websocket:
        response = client.post(
            "/leads",
            json={"meta_lead_id": "ws-001", "name": "WebSocket Lead"},
            headers=headers,
        )
        message = websocket.receive_json()
    assert response.status_code == 201
    assert message["type"] == "new_lead"
    assert message["data"]["meta_lead_id"] == "ws-001"


def test_websocket_ticket_cannot_access_leads_api(client, auth_token, websocket_ticket):
    response = client.get(
        "/leads",
        headers={"Authorization": f"Bearer {websocket_ticket}"},
    )
    assert response.status_code == 401


def test_websocket_rejects_unauthenticated_connection(client):
    with client.websocket_connect("/ws/leads") as websocket:
        with pytest.raises(WebSocketDisconnect) as disconnect:
            websocket.receive_text()
    assert disconnect.value.code == 4401


def test_webhook_signature_and_unexpected_payload(client):
    payload = b'{"object":"page","entry":[]}'
    signature = "sha256=" + hmac.new(b"app-secret", payload, hashlib.sha256).hexdigest()
    assert client.post("/webhook/meta", content=payload, headers={"X-Hub-Signature-256": "sha256=bad"}).status_code == 403
    response = client.post("/webhook/meta", content=payload, headers={"X-Hub-Signature-256": signature})
    assert response.status_code == 200
    assert response.json() == {"received": True}
    invalid_json = b"not-json"
    invalid_signature = "sha256=" + hmac.new(b"app-secret", invalid_json, hashlib.sha256).hexdigest()
    assert client.post(
        "/webhook/meta",
        content=invalid_json,
        headers={"X-Hub-Signature-256": invalid_signature},
    ).status_code == 400


def test_malformed_webhook_shapes_are_ignored(client):
    payload = b'{"entry":null}'
    signature = "sha256=" + hmac.new(b"app-secret", payload, hashlib.sha256).hexdigest()
    response = client.post("/webhook/meta", content=payload, headers={"X-Hub-Signature-256": signature})
    assert response.status_code == 200
    assert response.json() == {"received": True}


def test_meta_lead_event_fetches_persists_and_broadcasts(
    client,
    monkeypatch,
    auth_token,
    websocket_ticket,
):
    async def fake_fetch_lead(lead_id, form_id=None, page_id=None):
        return LeadCreate(
            meta_lead_id=lead_id,
            name="Meta Test",
            email="meta@example.com",
            phone="555-0100",
            form_id=form_id,
            page_id=page_id,
        )

    monkeypatch.setattr("app.routes.webhook.fetch_lead", fake_fetch_lead)
    payload = (
        b'{"object":"page","entry":[{"id":"page-123","changes":[{"field":"leadgen",'
        b'"value":{"leadgen_id":"meta-123","form_id":"form-456"}}]}]}'
    )
    signature = "sha256=" + hmac.new(b"app-secret", payload, hashlib.sha256).hexdigest()
    with client.websocket_connect(f"/ws/leads?ticket={websocket_ticket}") as websocket:
        response = client.post("/webhook/meta", content=payload, headers={"X-Hub-Signature-256": signature})
        message = websocket.receive_json()
    assert response.status_code == 200
    assert message["type"] == "new_lead"
    assert message["data"]["meta_lead_id"] == "meta-123"
    assert message["data"]["form_id"] == "form-456"
    assert message["data"]["page_id"] == "page-123"
    assert client.get(
        "/leads",
        headers={"Authorization": f"Bearer {auth_token}"},
    ).json()[0]["email"] == "meta@example.com"


def test_legacy_sqlite_leads_are_migrated(monkeypatch, tmp_path):
    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with legacy_engine.begin() as connection:
        connection.exec_driver_sql(
            """CREATE TABLE leads (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        connection.exec_driver_sql(
            "INSERT INTO leads (id, full_name, email, phone) VALUES ('legacy-1', 'Legacy Person', 'legacy@example.com', '555')"
        )

    monkeypatch.setattr(database_module, "engine", legacy_engine)
    database_module.initialize_database()
    with legacy_engine.connect() as connection:
        migrated = connection.exec_driver_sql("SELECT * FROM leads").mappings().one()
        tables = connection.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").scalars().all()
    assert migrated["meta_lead_id"] == "legacy-1"
    assert migrated["name"] == "Legacy Person"
    assert migrated["email"] == "legacy@example.com"
    assert "leads_legacy" not in tables
    legacy_engine.dispose()