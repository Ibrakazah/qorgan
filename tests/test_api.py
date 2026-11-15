from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[TestClient]:
    monkeypatch.setenv("QORGAN_DB", str(tmp_path / "q.db"))
    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_mock_mode(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["mock"] is True
    assert "scam_script" in body["tasks"]


def test_app_and_playground_are_served(client: TestClient) -> None:
    app_page = client.get("/")
    assert app_page.status_code == 200
    assert "Qorgan" in app_page.text
    assert client.get("/playground").status_code == 200


def test_scam_task_single_call(client: TestClient) -> None:
    response = client.post(
        "/v1/tasks/scam_script",
        json={"answer": "Звонил сотрудник службы безопасности банка, надо перевести на безопасный счёт"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["output"]["script"] == "fake_bank_security"
    assert body["meta"]["source"] == "mock"


@pytest.mark.parametrize("payload", [{"answer": ""}, {}, {"answer": "x" * 1501}])
def test_scam_task_rejects_invalid_input(client: TestClient, payload: dict[str, object]) -> None:
    assert client.post("/v1/tasks/scam_script", json=payload).status_code == 422


def test_unknown_task_is_404_with_hint(client: TestClient) -> None:
    response = client.post("/v1/tasks/nope", json={"answer": "x"})
    assert response.status_code == 404
    assert "scam_script" in response.json()["detail"]
