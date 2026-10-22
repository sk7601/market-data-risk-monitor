from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from market.database import Base, engine
from market.ingestion import ingest


@pytest.mark.parametrize(
    "page",
    ["Overview", "Market Explorer", "Portfolio Analyzer", "Data Quality Center", "Analyst Report"],
)
def test_pages(page, tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'ui.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    Base.metadata.create_all(engine(url))
    ingest(["SPY", "QQQ", "AAPL", "MSFT", "IWM"], "2024-01-02", "2024-12-31")
    app = AppTest.from_file(str(Path(__file__).parents[2] / "app/dashboard.py"))
    app.run(timeout=30)
    app.sidebar.radio[0].set_value(page).run(timeout=30)
    assert not app.exception
    assert not app.error
