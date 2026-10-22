import numpy as np
import pandas as pd
import pytest

from market.analytics import cumulative, drawdown, metrics, portfolio, returns, rolling_volatility


def test_hand_calculated_metrics():
    r = pd.Series([0.1, -0.1, 0.1])
    result = metrics(r)
    assert result["cumulative_return"] == pytest.approx(0.089)
    assert result["annualized_return"] == pytest.approx(1.089**84 - 1)
    assert result["daily_volatility"] == pytest.approx(np.std(r, ddof=1))
    assert result["annualized_volatility"] == pytest.approx(np.std(r, ddof=1) * np.sqrt(252))
    assert result["max_drawdown"] == pytest.approx(-0.1)
    assert result["historical_var_95"] == pytest.approx(0.08)
    assert cumulative(r).iloc[-1] == pytest.approx(0.089)
    assert drawdown(pd.Series([-0.2, 0.1])).min() == pytest.approx(-0.2)
    assert rolling_volatility(r, 2).iloc[1] == pytest.approx(
        np.std([0.1, -0.1], ddof=1) * np.sqrt(252)
    )


def test_returns_and_missing_session():
    p = pd.DataFrame(
        {"A": [100.0, 110.0, 121.0]},
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-05"]),
    )
    r = returns(p)
    assert r.iloc[0, 0] == pytest.approx(0.1)
    assert r.iloc[1:, 0].isna().all()


def test_portfolio():
    r = pd.DataFrame({"A": [0.1, -0.1, 0.1], "B": [0, 0.1, -0.1]})
    p, contributions = portfolio(r, {"A": 0.5, "B": 0.5})
    assert p.tolist() == pytest.approx([0.05, 0, 0])
    assert contributions.sum() == pytest.approx(p.std() * np.sqrt(252))
    p, contributions = portfolio(r * 0, {"A": 0.5, "B": 0.5})
    assert contributions.sum() == 0


@pytest.mark.parametrize(
    "r",
    [
        pd.Series([]),
        pd.Series([0.1]),
        pd.Series([0.1, np.nan]),
        pd.Series([-1.0, 0]),
        pd.Series([np.inf, 0]),
    ],
)
def test_bad_metrics(r):
    with pytest.raises(ValueError):
        metrics(r)


@pytest.mark.parametrize(
    "weights", [{"A": 1}, {"A": -0.1, "B": 1.1}, {"A": 0.2, "B": 0.2}, {"A": np.nan, "B": 0.5}]
)
def test_bad_weights(weights):
    with pytest.raises(ValueError):
        portfolio(pd.DataFrame({"A": [0.1, 0.2], "B": [0.2, 0.1]}), weights)


def test_other_edges():
    with pytest.raises(ValueError):
        metrics(pd.Series([0.1, 0.2]), 1)
    with pytest.raises(ValueError):
        rolling_volatility(pd.Series([0.1, 0.2]), 1)
    with pytest.raises(ValueError):
        portfolio(pd.DataFrame({"A": [np.nan, 0.1]}), {"A": 1})
    for p in [
        pd.DataFrame(),
        pd.DataFrame({"A": [1, 2]}),
        pd.DataFrame({"A": [1, -2]}, index=pd.date_range("2024-01-02", periods=2)),
        pd.DataFrame({"A": [1, 2]}, index=pd.to_datetime(["2024-01-03", "2024-01-02"])),
    ]:
        with pytest.raises(ValueError):
            returns(p)
