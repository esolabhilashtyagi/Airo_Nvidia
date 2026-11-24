import uuid

import pytest
from sqlalchemy.dialects import postgresql

from app.api.v1.companies import search_companies
from app.models.candidate import Company


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class FakeDatabase:
    def __init__(self, rows):
        self.rows = rows
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return FakeScalarResult(self.rows)


@pytest.mark.asyncio
async def test_company_search_returns_active_matches_and_normalizes_search_text():
    db = FakeDatabase([Company(id=uuid.uuid4(), name="Google", is_active=True)])

    response = await search_companies(search="  Google  ", limit=20, db=db)

    assert [item.name for item in response.data] == ["Google"]
    sql = str(db.statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "companies.is_active IS true" in sql
    assert "%%Google%%" in sql

