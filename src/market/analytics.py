"""Daily, USD, long-only analytics; 252 trading sessions per year."""

import numpy as np
import pandas as pd

from market.validation import trading_days


def returns(prices: pd.DataFrame) -> pd.DataFrame:
    if prices.empty or len(prices) < 2:
        raise ValueError("At least two observations required")
    if not isinstance(prices.index, pd.DatetimeIndex) or prices.index.has_duplicates:
        raise ValueError("Unique DatetimeIndex required")
    if not prices.index.is_monotonic_increasing:
        raise ValueError("Prices must be sorted")
    if (prices <= 0).any().any() or np.isinf(prices.to_numpy()).any():
        raise ValueError("Prices must be finite and positive")
    # Reindex BEFORE returns: missing sessions must not create multi-day daily returns.
    calendar = pd.DatetimeIndex(trading_days(prices.index.min(), prices.index.max()))
    return prices.reindex(calendar).pct_change(fill_method=None).iloc[1:]


def cumulative(r: pd.Series | pd.DataFrame):
    return (1 + r).cumprod() - 1


def drawdown(r: pd.Series) -> pd.Series:
    wealth = (1 + r).cumprod()
    return wealth / wealth.cummax().clip(lower=1) - 1


def metrics(r: pd.Series, confidence: float = 0.95) -> dict[str, float]:
    if not 0 < confidence < 1:
        raise ValueError("Confidence must be between zero and one")
    if len(r) < 2 or r.isna().any() or not np.isfinite(r).all() or (r <= -1).any():
        raise ValueError("At least two finite contiguous returns above -100% required")
    total = float((1 + r).prod() - 1)
    return {
        "cumulative_return": total,
        "annualized_return": float((1 + total) ** (252 / len(r)) - 1),
        "daily_volatility": float(r.std(ddof=1)),
        "annualized_volatility": float(r.std(ddof=1) * np.sqrt(252)),
        "max_drawdown": float(drawdown(r).min()),
        f"historical_var_{confidence * 100:g}": float(-r.quantile(1 - confidence)),
    }


def rolling_volatility(r: pd.Series, window: int = 21) -> pd.Series:
    if window < 2:
        raise ValueError("Window must be at least two")
    return r.rolling(window, min_periods=window).std(ddof=1) * np.sqrt(252)


def portfolio(r: pd.DataFrame, weights: dict[str, float]) -> tuple[pd.Series, pd.Series]:
    if set(weights) != set(r.columns):
        raise ValueError("One weight per instrument required")
    w = pd.Series(weights).reindex(r.columns)
    if not np.isfinite(w).all() or (w < 0).any() or not np.isclose(w.sum(), 1):
        raise ValueError("Long-only weights must sum to one")
    if len(r) < 2 or r.isna().any().any() or not np.isfinite(r.to_numpy()).all():
        raise ValueError("At least two aligned complete return rows required")
    p = r.dot(w).rename("Portfolio")
    covariance = r.cov() * 252
    vol = float(np.sqrt(w.dot(covariance).dot(w)))
    contribution = w * covariance.dot(w) / vol if vol > 0 else w * 0
    return p, contribution.rename("annualized_volatility_contribution")
