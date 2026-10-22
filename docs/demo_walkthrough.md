# Five-minute demonstration

1. Follow the README quick start. Confirm the source banner says SYNTHETIC and the 2024 range.
2. Overview: compare SPY/QQQ terminal returns and explain why these are simulated outcomes.
3. Market Explorer: zoom a price chart, inspect volume and 21-session volatility warm-up.
4. Portfolio Analyzer: set SPY=.6, QQQ=.4; compare benchmark and volatility contributions.
   Deliberately use weights totaling .9 to demonstrate validation, then repair them.
5. Data Quality Center: inspect run timestamps. Inject a duplicate/negative price through a
   test fixture and show the raw evidence, rule and run ID in automated tests.
6. Analyst Report: download HTML and CSV. Explain the 95% daily signed loss quantile.
7. Run pytest and open sql/analyst_queries.sql to explain LAG, CTE and ranking use cases.

A live provider fetch is optional and may be rate-limited. Select yahoo before viewing it.
Use a complete historical interval for analytics; missing sessions require repairing ingestion.
Screenshots are optional; this walkthrough describes functional interactions and no results
are represented as real investments or commercial impact.
