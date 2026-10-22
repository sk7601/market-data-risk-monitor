import pandas as pd
import pytest

from market.validation import trading_days, validate


def row(day="2024-01-02", **kw):
    return dict(date=day, open=100, high=102, low=99, close=101, volume=10, **kw)


def test_holiday():
    assert trading_days("2024-07-04", "2024-07-07") == [pd.Timestamp("2024-07-05").date()]
    clean, issues = validate(pd.DataFrame([row()]), "SPY", "2024-01-01", "2024-01-02")
    assert len(clean) == 1 and not issues


@pytest.mark.parametrize(
    "field,value,rule",
    [
        ("close", -1, "price"),
        ("high", 90, "ohlc"),
        ("volume", -1, "volume"),
        ("volume", 1.5, "volume"),
        ("open", None, "schema"),
        ("close", "x", "schema"),
        ("date", None, "schema"),
        ("date", "bad", "schema"),
        ("date", "2024-01-01", "session"),
    ],
)
def test_defects(field, value, rule):
    record = row()
    record[field] = value
    clean, issues = validate(pd.DataFrame([record]), "SPY", "2024-01-02", "2024-01-03")
    assert clean.empty
    assert rule in {i.rule for i in issues}
    assert "stale" in {i.rule for i in issues}


def test_duplicate_jump_flat_and_gap():
    rows = [
        row("2024-01-02"),
        row("2024-01-02"),
        dict(date="2024-01-03", open=150, high=151, low=149, close=150, volume=10),
    ]
    clean, issues = validate(pd.DataFrame(rows), "SPY", "2024-01-02", "2024-01-05")
    assert len(clean) == 2
    assert {"duplicate", "jump", "missing_session", "stale"} <= {i.rule for i in issues}
    assert next(i for i in issues if i.rule == "jump").severity == "warning"
    rows = [row(str(d)) for d in trading_days("2024-01-02", "2024-01-08")]
    _, issues = validate(pd.DataFrame(rows), "SPY", "2024-01-02", "2024-01-08")
    assert "flat" in {i.rule for i in issues}
    _, issues = validate(pd.DataFrame([{"date": "2024-01-02"}]), "SPY", "2024-01-02", "2024-01-02")
    assert "schema" in {i.rule for i in issues}
