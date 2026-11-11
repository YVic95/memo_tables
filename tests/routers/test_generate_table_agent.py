import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from database import get_db
from routers.generate_table_agent import router


@pytest.fixture
def api_client():
    app = FastAPI()
    app.include_router(router)
    db = object()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), db


@pytest.mark.parametrize(
    "general_tables",
    [
        [{"title": "One table", "headers": [], "rows": []}],
        [
            {"title": "First table", "headers": [], "rows": []},
            {"title": "Second table", "headers": [], "rows": []},
        ],
    ],
    ids=["single-table", "multiple-tables"],
)
def test_generation_response_exposes_only_general_tables(
    monkeypatch, api_client, general_tables
):
    client, db = api_client
    monkeypatch.setattr(
        "routers.generate_table_agent.get_language_pair_by_id",
        lambda session, pair_id: {
            "native_name": "English",
            "target_name": "Spanish",
        },
    )
    graph = MagicMock()
    graph.invoke.return_value = {
        "general_tables": general_tables,
        "fragmented_tables": [],
    }
    monkeypatch.setattr("routers.generate_table_agent.generate_table_graph", graph)

    response = client.post(
        "/api/generate-table",
        json={
            "grammar_rule_id": str(uuid.uuid4()),
            "language_pair_id": str(uuid.uuid4()),
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "general_tables": general_tables,
        "fragmented_tables": [],
    }
    assert "general_table" not in response.json()
    assert graph.invoke.call_args.args[0]["db"] is db
