from __future__ import annotations

from fastapi.testclient import TestClient


def _client_headers(token: str | None = None) -> dict[str, str]:
    headers = {"User-Agent": "pytest"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _login_admin(client: TestClient) -> str:
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123"},
        headers=_client_headers(),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["success"] is True, data
    return data["data"]["access_token"]


def test_records_crud_flow(reset_databases: None, sample_record: dict) -> None:
    # 延迟导入，确保读取测试环境变量
    from backend.main import app

    with TestClient(app) as client:
        token = _login_admin(client)

        # create
        r = client.post("/api/records", json=sample_record, headers=_client_headers(token))
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["success"] is True
        record_id = payload["data"]["id"]

        # list
        r = client.get("/api/records?page=1&per_page=15", headers=_client_headers())
        assert r.status_code == 200, r.text
        list_data = r.json()
        assert list_data["total"] >= 1
        assert any(item["id"] == record_id for item in list_data["records"])

        # get
        r = client.get(f"/api/records/{record_id}", headers=_client_headers())
        assert r.status_code == 200, r.text
        assert r.json()["id"] == record_id

        # update
        r = client.put(
            f"/api/records/{record_id}",
            json={"pressure": 12.5},
            headers=_client_headers(token),
        )
        assert r.status_code == 200, r.text
        assert r.json()["success"] is True

        # delete
        r = client.delete(f"/api/records/{record_id}", headers=_client_headers(token))
        assert r.status_code == 200, r.text
        assert r.json()["success"] is True

        # verify gone
        r = client.get(f"/api/records/{record_id}", headers=_client_headers())
        assert r.status_code == 404
