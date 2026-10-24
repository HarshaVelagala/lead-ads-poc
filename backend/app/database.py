from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL


def resolve_database_url(url: str = DATABASE_URL) -> str:
    if not url.startswith("sqlite:///"):
        return url
    path = url.removeprefix("sqlite:///")
    if path == ":memory:":
        return url
    if path.startswith("/"):
        return url
    absolute = Path(__file__).resolve().parents[1] / path
    absolute.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{absolute.as_posix()}"


DATABASE_URL_RESOLVED = resolve_database_url()
engine = create_engine(
    DATABASE_URL_RESOLVED,
    connect_args={"check_same_thread": False} if DATABASE_URL_RESOLVED.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    database: Session = SessionLocal()
    try:
        yield database
    finally:
        database.close()


def initialize_database() -> None:
    from app.models import Lead  # noqa: F401

    inspector = inspect(engine)
    legacy_leads = "leads" in inspector.get_table_names() and "meta_lead_id" not in {
        column["name"] for column in inspector.get_columns("leads")
    }
    if legacy_leads:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE leads RENAME TO leads_legacy"))

    Base.metadata.create_all(bind=engine)

    if legacy_leads:
        with engine.begin() as connection:
            rows = connection.execute(text("SELECT * FROM leads_legacy")).mappings().all()
            for row in rows:
                raw_created_at = row.get("created_at")
                try:
                    received_at = datetime.fromisoformat(raw_created_at) if raw_created_at else None
                except (TypeError, ValueError):
                    received_at = None
                connection.execute(
                    text(
                        """INSERT OR IGNORE INTO leads
                           (meta_lead_id, name, email, phone, received_at)
                           VALUES (:meta_lead_id, :name, :email, :phone, COALESCE(:received_at, CURRENT_TIMESTAMP))"""
                    ),
                    {
                        "meta_lead_id": str(row.get("id") or "") or None,
                        "name": row.get("full_name") or row.get("name") or "Legacy lead",
                        "email": row.get("email") or "",
                        "phone": row.get("phone") or "",
                        "received_at": received_at,
                    },
                )
            connection.execute(text("DROP TABLE leads_legacy"))