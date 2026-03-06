from __future__ import annotations

from fastapi.testclient import TestClient


def _headers() -> dict[str, str]:
    # security_middleware 会校验 User-Agent（缺失会被视为爬虫）
    return {"User-Agent": "pytest"}


def test_public_query_endpoints_smoke(reset_databases: None, sample_record: dict) -> None:
    """
    覆盖“公开查询”核心流程：
    - 写入一条样例记录
    - 验证 components / ranges / by-components / batch / range / hydrate 查询可用
    """
    from backend.database import batch_create_records
    from backend.main import app

    batch_create_records([sample_record])

    all_components = [
        "x_ch4",
        "x_c2h6",
        "x_c3h8",
        "x_co2",
        "x_n2",
        "x_h2s",
        "x_ic4h10",
    ]

    with TestClient(app) as client:
        # available components
        r = client.post(
            "/api/components/available",
            json={"selected": ["x_ch4"]},
            headers=_headers(),
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["success"] is True
        assert "x_c2h6" in payload["available"]

        # component ranges（同样需要全量组分，否则未选组分会被约束为接近 0）
        r = client.post(
            "/api/components/ranges",
            json={"components": all_components},
            headers=_headers(),
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["success"] is True
        assert "ranges" in payload and "x_ch4" in payload["ranges"]
        assert payload["temp_range"]["min"] <= sample_record["temperature"] <= payload["temp_range"]["max"]

        # by-components (需要全量组分，否则未选组分会被约束为接近 0)
        r = client.post(
            "/api/query/by-components",
            json={"components": all_components, "temperature": sample_record["temperature"]},
            headers=_headers(),
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["success"] is True
        assert abs(payload["data"]["pressure"] - sample_record["pressure"]) < 1e-9

        # batch query: 混合有效/无效温度
        r = client.post(
            "/api/query/batch",
            json={"components": all_components, "temperatures": [sample_record["temperature"], 50.0]},
            headers=_headers(),
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["success"] is True
        results = payload["data"]["results"]
        assert len(results) == 2
        assert results[0]["success"] in (True, False)
        assert results[1]["status"] == "invalid"

        # range query（全量组分）
        ranges = {k: {"min": v, "max": v} for k, v in sample_record.items() if k.startswith("x_")}
        r = client.post(
            "/api/query/range",
            json={"components": all_components, "ranges": ranges, "temperature": sample_record["temperature"]},
            headers=_headers(),
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["success"] is True
        assert abs(payload["data"]["pressure"] - sample_record["pressure"]) < 1e-9

        # match count（全量组分范围）
        r = client.post(
            "/api/query/match-count",
            json={"components": all_components, "ranges": ranges},
            headers=_headers(),
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["success"] is True
        assert payload["count"] >= 1
        assert payload["display"] in ("0", "<10", "10+", "100+")

        # hydrate query：全量组分精确匹配应得到满分
        r = client.post(
            "/api/query/hydrate",
            json={
                "components": {k: v for k, v in sample_record.items() if k.startswith("x_")},
                "temperature": sample_record["temperature"],
                "tolerance": 0.01,
            },
            headers=_headers(),
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["success"] is True
        assert payload["data"]["match_score"] == 100


def test_hydrate_query_no_match(reset_databases: None, sample_record: dict) -> None:
    from backend.database import batch_create_records
    from backend.main import app

    batch_create_records([sample_record])

    with TestClient(app) as client:
        # 仅给出 x_ch4，其它组分默认会被要求接近 0，因此应当匹配失败
        r = client.post(
            "/api/query/hydrate",
            json={"components": {"x_ch4": sample_record["x_ch4"]}, "temperature": sample_record["temperature"]},
            headers=_headers(),
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["success"] is False

