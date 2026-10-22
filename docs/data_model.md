# Relational model

`instruments`: unique symbol, exchange and USD currency. `daily_prices`: date and OHLCV,
source, adjustment policy, run FK and UTC ingestion timestamp. Unique instrument/date/source
permits separate real and synthetic histories without mixing them. Price and volume CHECKs
provide defense beyond Python validation; symbol/date indexes support chart reads.

`ingestion_runs`: source, started/finished UTC timestamps, status, accepted/rejected rows.
Run creation commits before work so transaction failures can be recorded independently.
The batch transaction writes all accepted rows and issues together; failures roll it back.
`validation_rules` holds rule descriptions; `data_quality_issues` references rule and run,
retaining instrument symbol, source-record date, severity, explanation and stringified raw JSON.
Dates in issues are text because malformed dates must remain auditable.

`portfolios` and `portfolio_holdings`: unique portfolio names and unique instrument allocations,
foreign keys and bounded weights. Aggregate sum-to-one is enforced by analytics, not a row CHECK.
The current UI computes ephemeral portfolios and does not expose a save operation.

Migrations: `alembic upgrade head`; destructive rollback on a disposable database:
`alembic downgrade base`. SQLite enables foreign keys explicitly; PostgreSQL provides production
constraints and concurrency. `sql/analyst_queries.sql` demonstrates CTEs, LAG, rolling sample
volatility, ranking and exception aggregation. SQL rolling windows count stored observations;
validate session completeness before interpreting them as sessions.
