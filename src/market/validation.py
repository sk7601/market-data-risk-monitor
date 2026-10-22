"""Validate raw observations before persistence, preserving record-level evidence."""

from dataclasses import asdict, dataclass
from datetime import date
from functools import lru_cache

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal

RULES = {
    "schema": "Required fields, parseable date and finite numeric types",
    "duplicate": "Duplicate symbol/date within this batch",
    "price": "Strictly positive OHLC prices",
    "ohlc": "Low <= open/close <= high",
    "volume": "Nonnegative integral volume",
    "session": "Observation must fall on an exchange session",
    "missing_session": "Expected NYSE session absent (also an unexpected gap)",
    "stale": "Latest record predates the final requested session",
    "jump": "Absolute simple close return exceeds 20%; review corporate actions",
    "flat": "Five identical closes: possible stale provider values",
}


@dataclass
class Finding:
    symbol: str
    date: str | None
    rule: str
    severity: str
    explanation: str
    record: dict

    def dictionary(self) -> dict:
        return asdict(self)


@lru_cache(maxsize=128)
def trading_days(start: date | str, end: date | str) -> list[date]:
    return list(mcal.get_calendar("NYSE").valid_days(start, end).date)


def validate(
    raw: pd.DataFrame, symbol: str, start: date | str, end: date | str
) -> tuple[pd.DataFrame, list[Finding]]:
    expected = set(trading_days(start, end))
    findings: list[Finding] = []
    accepted = []
    seen = set()

    def issue(day, rule, row, severity="error"):
        findings.append(
            Finding(
                symbol, day, rule, severity, RULES[rule], {str(k): str(v) for k, v in row.items()}
            )
        )

    for row in raw.to_dict("records"):
        try:
            day = pd.Timestamp(row["date"])
            if pd.isna(day):
                raise ValueError("Missing date")
            day = day.date()
            values = {k: float(row[k]) for k in ["open", "high", "low", "close", "volume"]}
            if not all(np.isfinite(v) for v in values.values()):
                raise ValueError("Nonfinite field")
        except (KeyError, ValueError, TypeError, OverflowError):
            issue(str(row.get("date")), "schema", row)
            continue
        errors = []
        if day in seen:
            errors.append("duplicate")
        seen.add(day)
        if day not in expected:
            errors.append("session")
        if min(values[k] for k in ["open", "high", "low", "close"]) <= 0:
            errors.append("price")
        if not (
            values["low"]
            <= min(values["open"], values["close"])
            <= max(values["open"], values["close"])
            <= values["high"]
        ):
            errors.append("ohlc")
        if values["volume"] < 0 or not values["volume"].is_integer():
            errors.append("volume")
        for rule in errors:
            issue(str(day), rule, row)
        if not errors:
            accepted.append({"date": day, **values})
    clean = pd.DataFrame(accepted, columns=["date", "open", "high", "low", "close", "volume"])
    clean = clean.sort_values("date").reset_index(drop=True)
    present = set(clean.date)
    for day in sorted(expected - present):
        issue(str(day), "missing_session", {}, "warning")
    if expected and (not present or max(present) < max(expected)):
        issue(str(max(expected)), "stale", {}, "warning")
    # Review adjacent expected sessions only: never label a multi-session change daily.
    positions = {day: i for i, day in enumerate(sorted(expected))}
    for i in range(1, len(clean)):
        a, b = clean.iloc[i - 1], clean.iloc[i]
        if positions[b.date] == positions[a.date] + 1 and abs(b.close / a.close - 1) > 0.2:
            issue(str(b.date), "jump", b.to_dict(), "warning")
    for i in range(4, len(clean)):
        block = clean.iloc[i - 4 : i + 1]
        if block.close.nunique() == 1:
            issue(str(block.iloc[-1].date), "flat", block.iloc[-1].to_dict(), "warning")
    return clean, findings
