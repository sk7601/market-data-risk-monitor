"""Read models serving the dashboard from persisted data."""

import pandas as pd
from sqlalchemy import select

from market.database import Instrument, Issue, Price, Run, engine
from market.validation import trading_days


def load(source: str, start: str, end: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    db = engine()
    query = (
        select(Instrument.symbol, Price.date, Price.close, Price.volume)
        .join(Price, Instrument.id == Price.instrument_id)
        .where(Price.source == source, Price.date >= start, Price.date <= end)
        .order_by(Price.date)
    )
    with db.connect() as conn:
        prices = pd.read_sql(query, conn)
        issues = pd.read_sql(
            select(Issue).join(Run, Issue.run_id == Run.id).where(Run.source == source), conn
        )
        runs = pd.read_sql(select(Run).where(Run.source == source), conn)
    prices["date"] = pd.to_datetime(prices.date)
    return prices, issues, runs


def complete_prices(prices: pd.DataFrame, symbols: list[str]) -> pd.DataFrame:
    wide = prices.pivot(index="date", columns="symbol", values="close").reindex(columns=symbols)
    if wide.empty:
        raise ValueError("No observations in selected range")
    days = pd.DatetimeIndex(trading_days(wide.index.min(), wide.index.max()))
    wide = wide.reindex(days)
    # Refuse to compound over internal gaps: user must choose a complete interval.
    if wide.isna().any().any():
        raise ValueError("Missing sessions: select a complete range or repair ingestion")
    return wide
