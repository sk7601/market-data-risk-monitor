-- Instrument returns: LAG compares adjacent stored rows. Inspect missing-session
-- exceptions first; this SQL alone does not guarantee adjacent exchange sessions.
WITH changes AS (
 SELECT instrument_id, date, close,
        close / LAG(close) OVER (PARTITION BY instrument_id, source ORDER BY date) - 1 AS ret
 FROM daily_prices WHERE source = 'synthetic'
), rolling AS (
 SELECT *, STDDEV_SAMP(ret) OVER (
   PARTITION BY instrument_id ORDER BY date ROWS BETWEEN 20 PRECEDING AND CURRENT ROW
 ) * SQRT(252) AS rolling_vol FROM changes
)
SELECT *, DENSE_RANK() OVER (PARTITION BY date ORDER BY rolling_vol DESC) AS risk_rank
FROM rolling ORDER BY date DESC;

-- Trace exceptions to their ingestion runs for operational follow-up.
SELECT r.id, r.status, i.symbol, i.rule, i.severity, COUNT(*) AS issue_count
FROM ingestion_runs r JOIN data_quality_issues i ON i.run_id = r.id
GROUP BY r.id, r.status, i.symbol, i.rule, i.severity ORDER BY issue_count DESC;
