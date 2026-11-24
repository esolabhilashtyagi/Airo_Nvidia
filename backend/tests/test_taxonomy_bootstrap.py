import uuid

import pytest
from sqlalchemy.engine import make_url

from app.core import bootstrap_taxonomy
from app.core import bootstrap_public_content
from app.core.bootstrap_taxonomy import ensure_baseline_taxonomy
from app.core.database_guards import validate_taxonomy_bootstrap_target
from app.models.candidate import Company
from app.models.taxonomy import Industry, IndustryCategory, JobRole


class MemoryQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model
        self.conditions = []

    def filter(self, *conditions):
        self.conditions.extend(conditions)
        return self

    def first(self):
        for row in self.db.rows:
            if isinstance(row, self.model) and all(
                getattr(row, condition.left.key) == condition.right.value
                for condition in self.conditions
            ):
                return row
        return None


class MemorySession:
    def __init__(self):
        self.rows = []

    def query(self, model):
        return MemoryQuery(self, model)

    def add(self, row):
        if row.id is None:
            row.id = uuid.uuid4()
        self.rows.append(row)

    def flush(self):
        return None

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


def test_baseline_taxonomy_bootstrap_is_idempotent_and_only_adds_taxonomy():
    db = MemorySession()

    first_added = ensure_baseline_taxonomy(db)
    second_added = ensure_baseline_taxonomy(db)

    assert first_added[0] > 0
    assert first_added[1] > 0
    assert first_added[2] > 0
    assert first_added[3] > 0
    assert second_added == (0, 0, 0, 0)
    assert any(isinstance(row, Company) for row in db.rows)
    assert all(isinstance(row, (Industry, IndustryCategory, JobRole, Company)) for row in db.rows)


def test_taxonomy_bootstrap_requires_production_and_exact_database_allowlist():
    url = "postgresql://user:pass@db.example/aairo_db"

    assert validate_taxonomy_bootstrap_target(url, "aairo_db", "production") == "aairo_db"
    with pytest.raises(RuntimeError, match="reserved for production"):
        validate_taxonomy_bootstrap_target(url, "aairo_db", "development")
    with pytest.raises(RuntimeError, match="required"):
        validate_taxonomy_bootstrap_target(url, None, "production")
    with pytest.raises(RuntimeError, match="does not match"):
        validate_taxonomy_bootstrap_target(url, "different_db", "production")


def test_bootstrap_connects_using_render_database_url_not_sync_localhost_default(monkeypatch):
    database_url = "postgresql+asyncpg://bootstrap_user:secret@managed-db.example:6543/aairo_db"
    captured = {}
    db = MemorySession()

    class FakeEngine:
        def dispose(self):
            captured["disposed"] = True

    monkeypatch.setattr(bootstrap_taxonomy.settings, "DATABASE_URL", database_url)
    monkeypatch.setattr(bootstrap_taxonomy.settings, "ENVIRONMENT", "production")
    monkeypatch.setenv("TAXONOMY_BOOTSTRAP_ALLOWED_DB", "aairo_db")
    monkeypatch.setattr(
        bootstrap_taxonomy,
        "create_engine",
        lambda url, **_kwargs: captured.setdefault("engine_url", url) and FakeEngine(),
    )
    monkeypatch.setattr(bootstrap_taxonomy, "sessionmaker", lambda **_kwargs: lambda: db)

    bootstrap_taxonomy.main()

    parsed = make_url(captured["engine_url"])
    assert parsed.host == "managed-db.example"
    assert parsed.port == 6543
    assert parsed.database == "aairo_db"
    assert captured["disposed"] is True


def test_public_content_bootstrap_uses_exact_allowlist_and_skips_demo_accounts(monkeypatch):
    database_url = "postgresql+asyncpg://bootstrap_user:secret@managed-db.example:6543/aairo_db"
    captured = {}

    class FakeEngine:
        def dispose(self):
            captured["disposed"] = True

    class FakeSession:
        def close(self):
            captured["session_closed"] = True

        def rollback(self):
            captured["rolled_back"] = True

    db = FakeSession()
    monkeypatch.setattr(bootstrap_public_content.settings, "DATABASE_URL", database_url)
    monkeypatch.setattr(bootstrap_public_content.settings, "ENVIRONMENT", "production")
    monkeypatch.setenv("PUBLIC_CONTENT_BOOTSTRAP_ALLOWED_DB", "aairo_db")
    monkeypatch.setattr(
        bootstrap_public_content,
        "create_engine",
        lambda url, **_kwargs: captured.setdefault("engine_url", url) and FakeEngine(),
    )
    monkeypatch.setattr(bootstrap_public_content, "sessionmaker", lambda **_kwargs: lambda: db)
    monkeypatch.setattr(bootstrap_public_content, "ensure_baseline_taxonomy", lambda _db: None)
    monkeypatch.setattr(
        bootstrap_public_content,
        "seed_database",
        lambda _db, **kwargs: captured.setdefault("seed_options", kwargs),
    )

    bootstrap_public_content.main()

    parsed = make_url(captured["engine_url"])
    assert parsed.host == "managed-db.example"
    assert parsed.port == 6543
    assert parsed.database == "aairo_db"
    assert captured["seed_options"] == {"include_demo_accounts": False}
    assert captured["session_closed"] is True
    assert captured["disposed"] is True
