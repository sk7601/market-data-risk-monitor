"""Escaped self-contained HTML exports without external rendering dependencies."""

from html import escape

import pandas as pd

from market.analytics import metrics


def report(symbol: str, r: pd.Series, warnings: list[str]) -> str:
    values = metrics(r)
    rows = "".join(f"<tr><td>{escape(k)}</td><td>{v:.4%}</td></tr>" for k, v in values.items())
    notes = "".join(f"<li>{escape(w)}</li>" for w in warnings)
    return (
        "<!doctype html><html><meta charset='utf-8'><title>Analyst report</title>"
        "<style>body{font:17px system-ui;max-width:900px;margin:50px auto}"
        "td{padding:10px;border-bottom:1px solid #ddd}</style>"
        f"<h1>{escape(symbol)} analyst report</h1><p>Daily adjusted USD series; "
        "252-session annualization. Historical risk does not predict future losses. "
        "Maximum drawdown measures the largest peak-to-trough loss, including the "
        "initial investment. VaR is a signed 95% daily loss quantile, not a loss limit."
        f"</p><table>{rows}</table><h2>Data quality</h2><ul>{notes}</ul></html>"
    )
