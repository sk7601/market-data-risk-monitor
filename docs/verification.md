# Verification evidence — 2026-10-22

- Windows, Python 3.13.5; NumPy 2.3.5, Pandas 2.3.3, SQLAlchemy 2.1.6.
- Full suite: **35 passed**. Core coverage: **99.13%** (analytics 100%; validation 99%).
- Coverage measures analytics.py and validation.py; other layers have integration/UI tests.
- Ruff lint and formatting checks pass. All five sections pass Streamlit AppTest.
- Sample ingestion: 1,260 accepted / 0 rejected; idempotency and failure audit tested.
- Live Yahoo SPY fetch and ingestion: four adjusted rows, January 2–5, 2024.
- Portable PostgreSQL 17.11 started on localhost:55432. Alembic upgrade, downgrade,
  upgrade succeeded; sample ingestion accepted 1,260 rows; PostgreSQL integration: **4 passed**.
- Streamlit launched on localhost:8501; `/_stcore/health` returned `ok`.
- `docker compose config --quiet` passed. **Compose startup not verified locally**:
  Docker's Linux engine is unavailable because WSL is absent. CI supplies PostgreSQL checks.
- GitHub Actions run [39722731472](https://github.com/sk7601/market-data-risk-monitor/actions/runs/39722731472)
  passed on Ubuntu, including the Docker Compose build, database readiness, migration,
  sample startup and HTTP health smoke check. Compose runtime is verified remotely.
- No paid API required. No secrets, environment files or local databases tracked.
- Full run emitted dependency metadata warnings and one in-memory SQLite test connection
  warning. That test now disposes its engine; targeted recheck: 15 passed.

Reproduce with README commands. No performance benchmarks or financial outcomes are claimed.
