# Mathematical definitions and boundary behavior

Let P be an adjusted closing price and r a daily simple return. r_t=P_t/P_(t-1)-1.
No imputation: missing exchange dates are inserted as NA before pct_change(fill_method=None).
Summary compounding requires a complete interval. USD is assumed throughout.

Wealth W_t=product_(i<=t)(1+r_i); cumulative return W_t-1. Geometric annualization
is W_n^(252/n)-1. Daily volatility is sample standard deviation with denominator n-1;
annualized volatility is s*sqrt(252), using the conventional independent-session scaling.
Rolling volatility uses 21 observations and returns NA until the full window exists.
Drawdown D_t=W_t/max(1,W_1,...,W_t)-1; maximum drawdown is min D_t (nonpositive).
Historical VaR_95=-Q_.05(r) using linear quantile interpolation, signed daily loss convention.
Confidence is fixed at 95% in the dashboard. It is not expected shortfall or a guaranteed bound.

Daily rebalanced portfolio return r_p,t=sum w_i*r_i,t with w_i>=0 and sum(w)=1.
Annualized covariance C=252*cov(r); volatility sqrt(w'Cw). Volatility contribution i is
w_i*(Cw)_i/sqrt(w'Cw); contributions sum to volatility and may be negative for a hedge.
For a zero-volatility portfolio contributions are zero. Returns must align on the same sessions
with no gaps and a consistent adjustment policy. Pairwise Pearson correlation is undefined
for constant series; the heatmap may show NA for those pairs. A benchmark is compared over
the same complete interval, and terminal percentage-point return difference is reported.

Hand fixtures include +10%,-10%,+10% => 8.9% cumulative return and -10% drawdown;
initial -20% is captured as drawdown. Equal weights on [10%,-10%,10%] and [0%,10%,-10%]
give [5%,0%,0%]. Tests cover negative/missing prices, bad weights, insufficient history,
calendar gaps, confidence and zero variance.
