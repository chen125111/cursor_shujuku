from __future__ import annotations


def test_crud_roundtrip(reset_databases: None, sample_record: dict) -> None:
    from backend.database import create_record, delete_record, get_record_by_id, update_record

    record_id = create_record(sample_record)
    row = get_record_by_id(record_id)
    assert row is not None
    assert row["id"] == record_id
    assert row["temperature"] == sample_record["temperature"]

    ok = update_record(record_id, {"pressure": 12.34})
    assert ok is True
    row2 = get_record_by_id(record_id)
    assert row2 is not None
    assert abs(row2["pressure"] - 12.34) < 1e-9

    deleted = delete_record(record_id)
    assert deleted is True
    assert get_record_by_id(record_id) is None


def test_get_all_records_filters(reset_databases: None, sample_record: dict) -> None:
    from backend.database import batch_create_records, get_all_records

    r1 = dict(sample_record)
    r2 = dict(sample_record)
    r2["temperature"] = 320.0
    r2["pressure"] = 2.0

    batch_create_records([r1, r2])

    res = get_all_records(page=1, per_page=50, temp_min=310.0)
    assert res["total"] == 1
    assert res["records"][0]["temperature"] == 320.0

    res2 = get_all_records(page=1, per_page=50, pressure_max=5.0)
    assert res2["total"] == 1
    assert res2["records"][0]["pressure"] == 2.0


def test_query_by_composition_strict_mode(reset_databases: None, sample_record: dict) -> None:
    from backend.database import batch_create_records, query_by_composition

    batch_create_records([sample_record])

    # strict_mode=True 时，未输入的组分要求接近 0（会导致不匹配）
    strict = query_by_composition(
        {"x_ch4": sample_record["x_ch4"]},
        tolerance=0.01,
        strict_mode=True,
    )
    assert strict == []

    relaxed = query_by_composition(
        {"x_ch4": sample_record["x_ch4"]},
        tolerance=0.01,
        strict_mode=False,
    )
    assert len(relaxed) == 1
    assert relaxed[0]["pressure"] == sample_record["pressure"]


def test_chart_data_shapes(reset_databases: None, sample_record: dict) -> None:
    from backend.database import batch_create_records, get_chart_data

    batch_create_records([sample_record])
    temp = get_chart_data("temperature")
    assert "labels" in temp and "data" in temp
    pressure = get_chart_data("pressure")
    assert "labels" in pressure and "data" in pressure
    scatter = get_chart_data("scatter")
    assert "data" in scatter
