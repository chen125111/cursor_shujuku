from __future__ import annotations

from fastapi.testclient import TestClient


def _headers() -> dict[str, str]:
    return {"User-Agent": "pytest"}


def _seed_public_query_records() -> None:
    from backend.database import create_record

    records = [
        {
            "temperature": 270.0,
            "pressure": 5.2,
            "x_ch4": 0.90,
            "x_c2h6": 0.10,
            "x_c3h8": 0.0,
            "x_co2": 0.0,
            "x_n2": 0.0,
            "x_h2s": 0.0,
            "x_ic4h10": 0.0,
        },
        {
            "temperature": 275.0,
            "pressure": 6.1,
            "x_ch4": 0.89,
            "x_c2h6": 0.11,
            "x_c3h8": 0.0,
            "x_co2": 0.0,
            "x_n2": 0.0,
            "x_h2s": 0.0,
            "x_ic4h10": 0.0,
        },
        {
            "temperature": 282.0,
            "pressure": 7.9,
            "x_ch4": 0.88,
            "x_c2h6": 0.12,
            "x_c3h8": 0.0,
            "x_co2": 0.0,
            "x_n2": 0.0,
            "x_h2s": 0.0,
            "x_ic4h10": 0.0,
        },
        {
            "temperature": 290.0,
            "pressure": 9.0,
            "x_ch4": 1.0,
            "x_c2h6": 0.0,
            "x_c3h8": 0.0,
            "x_co2": 0.0,
            "x_n2": 0.0,
            "x_h2s": 0.0,
            "x_ic4h10": 0.0,
        },
    ]
    for record in records:
        create_record(record)


def test_public_queries_and_performance_summary(reset_databases: None) -> None:
    _seed_public_query_records()

    from backend.main import app

    with TestClient(app) as client:
        r = client.post("/api/components/available", json={"selected": ["x_ch4"]}, headers=_headers())
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["success"] is True
        assert "x_c2h6" in payload["available"]
        assert payload["match_count"] >= 4

        r = client.post("/api/components/ranges", json={"components": ["x_ch4", "x_c2h6"]}, headers=_headers())
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["success"] is True
        assert payload["total_records"] == 3
        assert payload["temp_range"]["min"] == 270.0
        assert payload["temp_range"]["max"] == 282.0

        r = client.post(
            "/api/query/by-components",
            json={"components": ["x_ch4", "x_c2h6"], "temperature": 276.0},
            headers=_headers(),
        )
        assert r.status_code == 200, r.text
        assert "X-Request-ID" in r.headers
        payload = r.json()
        assert payload["success"] is True
        assert payload["data"]["temperature"] == 275.0
        assert abs(payload["data"]["pressure"] - 6.1) < 1e-6

        r = client.post(
            "/api/query/range",
            json={
                "components": ["x_ch4", "x_c2h6"],
                "ranges": {
                    "x_ch4": {"min": 0.87, "max": 0.91},
                    "x_c2h6": {"min": 0.09, "max": 0.13},
                },
                "temperature": 281.0,
            },
            headers=_headers(),
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["success"] is True
        assert payload["data"]["temperature"] == 282.0

        r = client.post(
            "/api/query/match-count",
            json={
                "components": ["x_ch4", "x_c2h6"],
                "ranges": {
                    "x_ch4": {"min": 0.87, "max": 0.91},
                    "x_c2h6": {"min": 0.09, "max": 0.13},
                },
            },
            headers=_headers(),
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["success"] is True
        assert payload["count"] == 3

        r = client.post(
            "/api/query/batch",
            json={"components": ["x_ch4", "x_c2h6"], "temperatures": [269.0, 276.0, 410.0]},
            headers=_headers(),
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["success"] is True
        results = payload["data"]["results"]
        assert results[0]["success"] is True
        assert results[1]["matched_temperature"] == 275.0
        assert results[2]["status"] == "invalid"

        r = client.post(
            "/api/query/hydrate",
            json={
                "components": {"x_ch4": 0.89, "x_c2h6": 0.11},
                "temperature": 275.0,
                "tolerance": 0.03,
            },
            headers=_headers(),
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["success"] is True
        assert payload["data"]["match_score"] >= 90

        r = client.get("/api/performance/summary", headers=_headers())
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["success"] is True
        assert payload["data"]["requests"]["total"] >= 7
        assert any(item["route"] == "POST /api/query/by-components" for item in payload["data"]["routes"])
        assert any(item["name"] == "public_query_by_components_candidates" for item in payload["data"]["queries"])
