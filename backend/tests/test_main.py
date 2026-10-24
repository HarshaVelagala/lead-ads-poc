import hashlib
import hmac

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database as database_module
from app.database import Base, get_db
from app.main import app
from app.models.lead import Lead
from app.schemas.lead import LeadCreate
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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_health_and_lead_crud(client):
    assert client.get("/health").json() == {"status": "ok"}
    created = client.post(
        "/leads",
        json={"meta_lead_id": "meta-001", "name": "Test Lead", "email": "test@example.com", "phone": "123"},
    )
    assert created.status_code == 201
    lead = created.json()
    assert lead["meta_lead_id"] == "meta-001"
    assert lead["fullName"] == "Test Lead"
    assert lead["mobile_id"] == "meta-001"
    assert client.get("/leads").json()[0]["email"] == "test@example.com"
    assert client.get(f"/leads/{lead['id']}").json()["name"] == "Test Lead"
    assert client.get("/leads/999").status_code == 404


def test_meta_webhook_verification(client):
    response = client.get(
        "/webhook/meta",
        params={"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "12345"},
    )
    assert response.status_code == 200
    assert response.text == "12345"
    assert client.get("/webhook/meta", params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "1"}).status_code == 403


def test_duplicate_meta_lead_is_not_inserted_twice(client):
    payload = {"meta_lead_id": "duplicate-1", "name": "Same Lead"}
    first = client.post("/leads", json=payload)
    second = client.post("/leads", json=payload)
    assert first.status_code == second.status_code == 201
    assert len(client.get("/leads").json()) == 1


def test_websocket_broadcasts_created_lead(client):
    with client.websocket_connect("/ws/leads") as websocket:
        response = client.post("/leads", json={"meta_lead_id": "ws-001", "name": "WebSocket Lead"})
        message = websocket.receive_json()
    assert response.status_code == 201
    assert message["type"] == "new_lead"
    assert message["data"]["meta_lead_id"] == "ws-001"


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


def test_meta_lead_event_fetches_persists_and_broadcasts(client, monkeypatch):
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
    with client.websocket_connect("/ws/leads") as websocket:
        response = client.post("/webhook/meta", content=payload, headers={"X-Hub-Signature-256": signature})
        message = websocket.receive_json()
    assert response.status_code == 200
    assert message["type"] == "new_lead"
    assert message["data"]["meta_lead_id"] == "meta-123"
    assert message["data"]["form_id"] == "form-456"
    assert message["data"]["page_id"] == "page-123"
    assert client.get("/leads").json()[0]["email"] == "meta@example.com"


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