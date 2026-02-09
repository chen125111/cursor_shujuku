from __future__ import annotations

from backend.data_validation import (
    PRESSURE_SOFT_MAX,
    clean_record,
    count_soft_warnings,
    get_soft_warnings,
    validate_partial_record,
    validate_record,
)


def test_validate_record_ok(sample_record: dict) -> None:
    ok, errors = validate_record(sample_record)
    assert ok is True
    assert errors == []


def test_validate_record_requires_mole_fraction_sum(sample_record: dict) -> None:
    bad = dict(sample_record)
    bad["x_ch4"] = 0.0
    bad["x_c2h6"] = 0.0
    bad["x_c3h8"] = 0.0
    bad["x_co2"] = 0.0
    bad["x_n2"] = 0.0
    bad["x_h2s"] = 0.0
    bad["x_ic4h10"] = 0.0

    ok, errors = validate_record(bad)
    assert ok is False
    assert any("摩尔分数不能全部为 0" in e for e in errors)


def test_validate_partial_record_ignores_required_rules() -> None:
    ok, errors = validate_partial_record({"pressure": 3.0})
    assert ok is True
    assert errors == []


def test_clean_record_coerces_types_and_defaults() -> None:
    cleaned = clean_record({"temperature": "300", "pressure": "", "x_ch4": None})
    assert cleaned["temperature"] == 300.0
    assert cleaned["pressure"] == 0.0
    assert cleaned["x_ch4"] == 0.0


def test_soft_warnings_pressure(sample_record: dict) -> None:
    rec = dict(sample_record)
    rec["pressure"] = PRESSURE_SOFT_MAX + 1.0
    warnings = get_soft_warnings(rec)
    assert any("压力" in w for w in warnings)


def test_count_soft_warnings(sample_record: dict) -> None:
    r1 = dict(sample_record)
    r2 = dict(sample_record)
    r2["pressure"] = PRESSURE_SOFT_MAX + 0.1
    assert count_soft_warnings([r1, r2]) == 1
