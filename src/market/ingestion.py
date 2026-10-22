"""Provider adapter, reproducible sample, audited idempotent upserts."""

import argparse
import json
import logging
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from market.database import Instrument, Issue, Price, Rule, Run, sessions, utcnow
from market.validation import RULES, trading_days, validate

log = logging.getLogger(__name__)
SYMBOLS = ["SPY", "QQQ", "AAPL", "MSFT", "IWM"]
SAMPLE_START, SAMPLE_END = "2024-01-02", "2024-12-31"


def sample(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    days = trading_days(SAMPLE_START, SAMPLE_END)
    common = rng.normal(0.0003, 0.009, len(days))
    rows = []
    for i, symbol in enumerate(SYMBOLS):
        prices = (100 + i * 30) * np.exp(np.cumsum(common + rng.normal(0, 0.005, len(days))))
        for day, close in zip(days, prices, strict=True):
            opening = close * (1 + rng.normal(0, 0.002))
            rows.append(
                dict(
                    symbol=symbol,
                    date=day,
                    open=opening,
                    high=max(opening, close) * 1.005,
                    low=min(opening, close) * 0.995,
                    close=close,
                    volume=int(rng.integers(100000, 10000000)),
                )
            )
    return pd.DataFrame(rows)


def fetch(symbol: str, start: str, end: str, attempts: int = 3) -> pd.DataFrame:
    import yfinance as yf

    error = None
    for attempt in range(attempts):
        try:
            frame = yf.Ticker(symbol).history(
                start=start,
                end=str(date.fromisoformat(end) + timedelta(days=1)),
                auto_adjust=True,
                raise_errors=True,
                timeout=15,
            )
            if frame.empty:
                raise ValueError("Provider returned no observations")
            frame = frame.reset_index()
            frame.columns = [str(c).lower() for c in frame.columns]
            frame["date"] = pd.to_datetime(frame["date"]).dt.date
            return frame
        except Exception as exc:
            error = type(exc).__name__
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise RuntimeError(f"Provider failed after {attempts} attempts ({error})")


def ingest(
    symbols: list[str],
    start: str,
    end: str,
    source: str = "synthetic",
    url: str | None = None,
    frames: dict[str, pd.DataFrame] | None = None,
) -> int:
    if date.fromisoformat(start) > date.fromisoformat(end) or not symbols:
        raise ValueError("Select symbols and an ordered date range")
    if source not in {"synthetic", "yahoo"}:
        raise ValueError("Unsupported provider")
    if any(s not in SYMBOLS for s in symbols):
        raise ValueError("Unsupported instrument")
    factory = sessions(url)
    with factory.begin() as db:
        run = Run(source=source)
        db.add(run)
        db.flush()
        run_id = run.id
    try:
        bundled = None
        if source == "synthetic" and frames is None:
            path = Path(__file__).resolve().parents[2] / "data/samples/prices.csv"
            bundled = pd.read_csv(path) if path.exists() else sample()
        with factory.begin() as db:
            for code, description in RULES.items():
                if db.get(Rule, code) is None:
                    db.add(Rule(code=code, description=description))
            db.flush()
            accepted = rejected = 0
            for symbol in symbols:
                raw = (
                    frames[symbol]
                    if frames is not None
                    else (
                        bundled[bundled.symbol == symbol].copy()
                        if bundled is not None
                        else fetch(symbol, start, end)
                    )
                )
                if source == "synthetic" and frames is None:
                    dates = pd.to_datetime(raw.date).dt.date
                    raw = raw[
                        (dates >= date.fromisoformat(start)) & (dates <= date.fromisoformat(end))
                    ]
                clean, issues = validate(raw, symbol, start, end)
                inst = db.scalar(select(Instrument).where(Instrument.symbol == symbol))
                if inst is None:
                    inst = Instrument(symbol=symbol)
                    db.add(inst)
                    db.flush()
                for row in clean.to_dict("records"):
                    values = dict(
                        **row,
                        instrument_id=inst.id,
                        source=source,
                        run_id=run_id,
                        adjustment="synthetic"
                        if source == "synthetic"
                        else "split_dividend_adjusted",
                        ingested_at=utcnow(),
                    )
                    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
                    stmt = insert(Price).values(**values)
                    db.execute(
                        stmt.on_conflict_do_update(
                            index_elements=["instrument_id", "date", "source"], set_=values
                        )
                    )
                db.add_all(Issue(run_id=run_id, **finding.dictionary()) for finding in issues)
                accepted += len(clean)
                rejected += len(raw) - len(clean)
            run = db.get(Run, run_id)
            run.accepted, run.rejected = accepted, rejected
            run.status = "completed_with_rejections" if rejected else "completed"
            run.finished_at = utcnow()
        log.info(
            json.dumps(
                {
                    "event": "ingestion_completed",
                    "run_id": run_id,
                    "accepted": accepted,
                    "rejected": rejected,
                }
            )
        )
    except Exception as exc:
        with factory.begin() as db:
            run = db.get(Run, run_id)
            run.status, run.message, run.finished_at = "failed", type(exc).__name__, utcnow()
        log.error(
            json.dumps(
                {"event": "ingestion_failed", "run_id": run_id, "error_type": type(exc).__name__}
            )
        )
        raise
    return run_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["synthetic", "yahoo"], default="synthetic")
    parser.add_argument("--symbols", nargs="+", default=SYMBOLS)
    parser.add_argument("--start", default=SAMPLE_START)
    parser.add_argument("--end", default=SAMPLE_END)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(ingest(args.symbols, args.start, args.end, args.source))


if __name__ == "__main__":
    main()
