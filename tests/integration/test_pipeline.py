import os

import pandas as pd
import pytest
from sqlalchemy import func, select

from market.database import Base, Price, Run, engine, sessions
from market.ingestion import ingest, sample
from market.reporting import report


@pytest.fixture
def url(tmp_path):
    value = os.getenv("TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'integration.db'}")
    db = engine(value)
    Base.metadata.drop_all(db)
    Base.metadata.create_all(db)
    yield value
    Base.metadata.drop_all(db)


def test_idempotency_and_failure(url):
    data = sample()
    pd.testing.assert_frame_equal(data, sample())
    ingest(["SPY"], "2024-01-02", "2024-01-05", url=url)
    ingest(["SPY"], "2024-01-02", "2024-01-05", url=url)
    with sessions(url)() as db:
        assert db.scalar(select(func.count()).select_from(Price)) == 4
        assert db.scalar(select(func.count()).select_from(Run)) == 2
    with pytest.raises(KeyError):
        ingest(["SPY"], "2024-01-02", "2024-01-05", url=url, frames={})
    with sessions(url)() as db:
        assert db.scalars(select(Run).order_by(Run.id.desc())).first().status == "failed"


def test_report():
    html = report("<script>", pd.Series([0.1, -0.1]), ["<unsafe>"])
    assert "&lt;script&gt;" in html and "&lt;unsafe&gt;" in html


def test_provider_retry_and_empty(monkeypatch):
    import yfinance

    from market.ingestion import fetch

    class EmptyProvider:
        def history(self, **kwargs):
            return pd.DataFrame()

    monkeypatch.setattr(yfinance, "Ticker", lambda symbol: EmptyProvider())
    monkeypatch.setattr("market.ingestion.time.sleep", lambda delay: None)
    with pytest.raises(RuntimeError, match="3 attempts"):
        fetch("SPY", "2024-01-02", "2024-01-05")


def test_rejections_recorded(url):
    from market.database import Issue

    raw = pd.DataFrame([dict(date="2024-01-02", open=-1, high=2, low=-2, close=1, volume=10)])
    run_id = ingest(["SPY"], "2024-01-02", "2024-01-02", url=url, frames={"SPY": raw})
    with sessions(url)() as db:
        assert db.get(Run, run_id).rejected == 1
        assert db.scalar(select(func.count()).select_from(Price)) == 0
        assert db.scalar(select(func.count()).select_from(Issue)) > 0
