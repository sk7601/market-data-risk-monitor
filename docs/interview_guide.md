# Interview preparation

## 45-second explanation

I built a market-data quality and portfolio risk workspace for an analyst who needs to know
whether prices are trustworthy before interpreting risk. A repeatable pipeline validates
OHLCV records using the NYSE session calendar, quarantines hard failures and stores audit
results in PostgreSQL. Streamlit presents historical returns, volatility, drawdown, portfolio
comparisons and downloadable evidence-based reports. Tests use hand-verifiable return series.
The bundled demonstration is synthetic; a separate adapter supports adjusted Yahoo history.

## Two-minute explanation

The central problem is that convincing charts can conceal bad input data. My design records
an ingestion run first, fetches or loads raw observations, and validates every row. Negative
prices and inconsistent OHLC ranges are rejected, while large returns are review warnings
because genuine events can move prices. Exchange holidays are excluded using a calendar.
Accepted observations are upserted under an instrument/date/source key, so reruns do not
inflate history. Issues retain source fields and a run ID for investigation.

Analytics only compound contiguous, consistently adjusted daily series. I use simple returns,
252-session annualization, sample volatility, initial-wealth-aware drawdown and historical
95% VaR. Portfolios are long-only and rebalance daily with no costs. Risk contributions use
the covariance matrix and add to portfolio volatility. The interface includes exploration,
quality audits and escaped HTML/CSV exports. SQLite gives a simple offline demo; PostgreSQL,
Alembic, Docker Compose and GitHub Actions support reproducibility. I can explain each formula,
show tests that fail on deliberately defective inputs and discuss provider licensing and
survivorship limitations rather than claiming the tool predicts future risk.

## Execution and decisions

Entry points: `market.ingestion` and `app/dashboard.py`. Read database.py, validation.py,
ingestion.py, analytics.py, services.py, reporting.py in that order. SQLAlchemy constrains
storage; Alembic versions it. Pandas aligns series, NumPy supplies covariance arithmetic,
pandas-market-calendars defines exchange sessions, Plotly provides interactive charts.
PostgreSQL is a single relational store because this volume does not need distributed services.
See SQL examples for session returns, rolling risk ranks and operational exception counts.
Tests separately check pure math, row validation, persistence idempotency, failure audits,
report escaping and all five Streamlit views. Core coverage excludes UI/provider code explicitly.

## Ten likely questions

1. **Why simple returns?** They aggregate cross-sectionally under daily portfolio weights;
   log returns do not form a weighted portfolio return in the same way.
2. **Why not add daily returns?** Compounding multiplies wealth; +10% then -10% loses 1%.
3. **What does volatility measure?** Dispersion of daily returns, not maximum possible loss.
4. **How is drawdown different?** It measures path-dependent decline from a previous wealth peak.
5. **Why 252?** Conventional annual session count; actual calendars vary and the convention is explicit.
6. **Why adjusted prices?** Splits and dividends can distort raw-close economic return comparisons.
7. **Why calendar validation?** Weekends/holidays are not missing sessions; suspended instruments
   still need a more specific calendar explanation beyond this demo.
8. **How do weights affect risk?** Covariances matter; portfolio volatility is not weighted volatility.
9. **What does VaR miss?** Tail loss severity beyond the quantile, regime changes and small-sample error.
10. **How do reruns work?** Source-specific uniqueness and upserts replace observations while retaining
    separate run audits; rejected records never enter the analytical price table.

## Trade-offs and follow-up challenges

Trade-offs: unofficial provider versus licensed feed; daily rebalance versus buy-and-hold;
strict gap rejection versus imputation; metadata-based initial migration versus fully explicit DDL;
a single worker versus coordinating concurrent pipelines. Never claim unmeasured scalability.

Challenges: implement monthly rebalancing; include transaction costs; add expected shortfall;
track provider revisions; distinguish symbol suspensions from outages. For each, first define
semantics, add a small manual fixture, then change persistence/presentation as necessary.

## Ordered learning checklist

1. OHLCV, corporate actions and source provenance — 45 minutes.
2. Simple returns, compounding and 252-session annualization — 60 minutes.
3. Sample variance, covariance, Pearson correlation and risk contribution — 90 minutes.
4. Drawdown, historical quantiles and VaR limits — 45 minutes.
5. ORM constraints, upserts, transactions, Alembic and SQL windows — 90 minutes.
6. Validation severities, holiday calendars and audit traceability — 45 minutes.
7. Streamlit filters, report exports and error states — 30 minutes.
8. Run tests, inspect coverage and rehearse the demo — 60 minutes.

A TPA translates stakeholder questions into precise definitions, checks input quality,
investigates exceptions and communicates what evidence does and does not support. Demonstrate
those habits rather than presenting historical risk as an investment recommendation.
