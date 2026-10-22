"""SQL-backed market and portfolio workspace."""

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from market.analytics import cumulative, drawdown, metrics, portfolio, returns, rolling_volatility
from market.ingestion import SYMBOLS, ingest
from market.reporting import report
from market.services import complete_prices, load

st.set_page_config(page_title="Market Intelligence", page_icon="📈", layout="wide")
st.markdown(
    "<style>.block-container{padding-top:2rem}"
    "[data-testid=stMetric]{background:#eef4fa;padding:18px;border-radius:10px;"
    "color:#102a43}</style>",
    unsafe_allow_html=True,
)
st.title("Market Intelligence")
st.caption("DATA QUALITY / PERFORMANCE / PORTFOLIO RISK")
section = st.sidebar.radio(
    "Workspace",
    ["Overview", "Market Explorer", "Portfolio Analyzer", "Data Quality Center", "Analyst Report"],
)
source = st.sidebar.selectbox("Data source", ["synthetic", "yahoo"])
st.sidebar.caption("Synthetic is a seeded demonstration, never actual market performance.")
dates = st.sidebar.date_input(
    "Observation range",
    value=(pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-12-31").date()),
)
if len(dates) != 2:
    st.info("Select a start and end date.")
    st.stop()
start, end = map(str, dates)
if st.sidebar.button("Ingest selected range"):
    try:
        with st.spinner("Fetching, validating and storing observations..."):
            run = ingest(SYMBOLS, start, end, source)
        st.sidebar.success(f"Recorded ingestion run {run}")
    except Exception as exc:
        st.sidebar.error(
            f"Ingestion failed ({type(exc).__name__}). Review run status or use sample."
        )
try:
    prices, issues, runs = load(source, start, end)
except SQLAlchemyError:
    st.error(
        "Database unavailable or not migrated. Run alembic upgrade head, then load sample data."
    )
    st.stop()
if prices.empty:
    st.info("No observations. Ingest this range or select a populated source.")
    st.stop()
st.caption(f"{source.upper()} · USD · {prices.date.min().date()} → {prices.date.max().date()}")

if section == "Data Quality Center":
    st.subheader("Exception evidence and ingestion audit")
    for symbol, group in prices.groupby("symbol"):
        st.write(f"**{symbol}** · latest stored observation: {group.date.max().date()}")
    if not issues.empty:
        st.dataframe(
            issues.groupby(["symbol", "severity"]).size().rename("exceptions").reset_index(),
            hide_index=True,
        )
        severity = st.selectbox("Severity", ["all", "error", "warning"])
        query = st.text_input("Search exceptions")
        filtered = issues if severity == "all" else issues[issues.severity == severity]
        if query:
            filtered = filtered[
                filtered.astype(str)
                .apply(lambda col: col.str.contains(query, case=False, regex=False))
                .any(axis=1)
            ]
        st.dataframe(filtered, hide_index=True)
    else:
        st.success("No exceptions recorded for this source.")
    st.caption("Audit includes all runs for this source; exceptions retain run IDs and raw fields.")
    st.dataframe(runs, hide_index=True)
else:
    symbols = st.multiselect("Instruments", SYMBOLS, default=["SPY", "QQQ"])
    if not symbols:
        st.info("Select at least one instrument.")
        st.stop()
    try:
        wide = complete_prices(prices, symbols)
        r = returns(wide)
        if r.isna().any().any() or len(r) < 2:
            raise ValueError("At least three prices per instrument and no session gaps required")
        selected = st.selectbox("Focus instrument", symbols)
        summary = metrics(r[selected])
        if section == "Overview":
            st.subheader(f"{selected} performance snapshot")
            columns = st.columns(3)
            for col, key in zip(
                columns, ["cumulative_return", "annualized_volatility", "max_drawdown"], strict=True
            ):
                col.metric(key.replace("_", " ").title(), f"{summary[key]:.2%}")
            st.write("Latest observation:", str(wide.index.max().date()))
            st.write("Recorded quality exceptions:", len(issues[issues.symbol == selected]))
            st.plotly_chart(px.line(cumulative(r), title="Cumulative return"), width="stretch")
        elif section == "Market Explorer":
            st.plotly_chart(
                px.line(wide, title="Adjusted closing prices / synthetic prices"), width="stretch"
            )
            st.plotly_chart(
                px.bar(
                    prices[prices.symbol == selected], x="date", y="volume", title="Daily volume"
                ),
                width="stretch",
            )
            st.plotly_chart(px.line(r, title="Simple daily returns"), width="stretch")
            st.plotly_chart(
                px.line(rolling_volatility(r[selected]), title="21-session volatility"),
                width="stretch",
            )
        elif section == "Portfolio Analyzer":
            st.caption(
                "Long-only; weights sum to 1. Daily rebalancing, no costs, fractional holdings."
            )
            weights = {
                s: st.number_input(f"{s} weight", 0.0, 1.0, 1 / len(symbols), 0.05) for s in symbols
            }
            benchmark = st.selectbox("Benchmark", SYMBOLS)
            combined = returns(complete_prices(prices, list(dict.fromkeys(symbols + [benchmark]))))
            p, contributions = portfolio(combined[symbols], weights)
            compare = pd.concat([p, combined[benchmark].rename(benchmark)], axis=1)
            st.plotly_chart(
                px.line(cumulative(compare), title="Portfolio versus benchmark"), width="stretch"
            )
            st.metric(
                "Terminal benchmark-relative return (percentage points)",
                f"{(cumulative(p).iloc[-1] - cumulative(combined[benchmark]).iloc[-1]) * 100:.2f}",
            )
            st.dataframe(pd.Series(metrics(p), name="Portfolio metrics"))
            st.plotly_chart(
                px.bar(contributions, title="Additive contributions to annualized volatility"),
                width="stretch",
            )
            st.plotly_chart(
                px.imshow(
                    combined[symbols].corr(),
                    zmin=-1,
                    zmax=1,
                    color_continuous_scale="RdBu",
                    title="Return correlations",
                ),
                width="stretch",
            )
            st.plotly_chart(px.area(drawdown(p), title="Portfolio drawdown"), width="stretch")
        else:
            descriptions = {
                "SPY": "Broad US large-cap equity ETF",
                "QQQ": "Nasdaq-100 ETF",
                "IWM": "US small-cap equity ETF",
                "AAPL": "Apple common equity",
                "MSFT": "Microsoft common equity",
            }
            st.write(descriptions[selected])
            notes = issues[issues.symbol == selected].explanation.tolist()
            notes.insert(0, f"Data source: {source}. This range is historical, not a live quote.")
            html = report(selected, r[selected], notes)
            st.dataframe(pd.Series(summary, name="Value"))
            st.write(
                "Higher volatility means more variable historical daily returns. Drawdown "
                "describes historical peak-to-trough loss; neither bounds future risk."
            )
            for note in notes:
                st.write(note)
            st.download_button("Download HTML report", html, "analyst-report.html", "text/html")
            st.download_button("Download return CSV", r.to_csv(), "returns.csv", "text/csv")
    except (ValueError, KeyError) as exc:
        st.warning(str(exc))
