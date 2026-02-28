"""
Monte Carlo Simulation Module
==============================
Runs N simulations with randomised key inputs to build probability
distributions for revenue, EBITDA, share price, and other outputs.
"""

import numpy as np
from dataclasses import replace
from typing import Dict, List, Tuple
from financial_model import ModelAssumptions, YearResult, run_model


# ---------------------------------------------------------------------------
# Distribution definitions for key uncertain inputs
# ---------------------------------------------------------------------------

PARAMETER_DISTRIBUTIONS = {
    # (mean, std_dev, min_clip, max_clip)
    "partner_growth_rate":        (0.04,  0.02,  -0.02, 0.10),
    "rpp_target_m":               (4.1,   0.30,   3.2,  5.0),
    "gross_margin_target_pct":    (0.55,  0.03,   0.45, 0.62),
    "operating_margin_target_pct":(0.32,  0.04,   0.20, 0.40),
    "market_studies_pct":         (0.50,  0.08,   0.25, 0.70),
    "borrowing_rate":             (0.065, 0.015,  0.03, 0.12),
    "structural_debt_m":          (100.0, 20.0,   60.0, 180.0),
    "tax_rate":                   (0.21,  0.02,   0.15, 0.28),
    "working_capital_days":       (120,   15,     80,   160),
}


def sample_assumptions(base: ModelAssumptions, rng: np.random.Generator) -> ModelAssumptions:
    """Generate one randomised set of assumptions."""
    overrides = {}
    for param, (mean, std, lo, hi) in PARAMETER_DISTRIBUTIONS.items():
        val = rng.normal(mean, std)
        val = np.clip(val, lo, hi)
        # Ensure market_studies_pct and transformation_strategy_pct sum to 1
        if param == "market_studies_pct":
            overrides["market_studies_pct"] = val
            overrides["transformation_strategy_pct"] = 1.0 - val
        elif param == "working_capital_days":
            overrides[param] = int(round(val))
        else:
            overrides[param] = float(val)

    return replace(base, **overrides)


def run_monte_carlo(
    n_simulations: int = 5000,
    seed: int = 42,
    base: ModelAssumptions = None,
) -> Dict[str, np.ndarray]:
    """
    Run Monte Carlo simulation.

    Returns a dict mapping metric names to arrays of shape (n_simulations, n_years+1).
    """
    if base is None:
        base = ModelAssumptions()

    rng = np.random.default_rng(seed)
    n_years = base.forecast_years + 1

    # Pre-allocate output arrays
    metrics = [
        "revenue", "gross_profit", "gross_margin", "operating_profit",
        "operating_margin", "ebitda", "net_income", "share_price",
        "dividend_per_share", "partner_bonus", "per_partner_comp",
        "working_capital", "equity_value", "enterprise_value",
    ]
    arrays = {m: np.zeros((n_simulations, n_years)) for m in metrics}

    # Also store sampled input parameters for sensitivity analysis
    input_params = {p: np.zeros(n_simulations) for p in PARAMETER_DISTRIBUTIONS}

    for i in range(n_simulations):
        assumptions = sample_assumptions(base, rng)

        # Record sampled inputs
        for p in PARAMETER_DISTRIBUTIONS:
            input_params[p][i] = getattr(assumptions, p)

        results = run_model(assumptions)

        for j, r in enumerate(results):
            arrays["revenue"][i, j] = r.total_revenue_m
            arrays["gross_profit"][i, j] = r.gross_profit_m
            arrays["gross_margin"][i, j] = r.gross_margin_pct
            arrays["operating_profit"][i, j] = r.operating_profit_m
            arrays["operating_margin"][i, j] = r.operating_margin_pct
            arrays["ebitda"][i, j] = r.ebitda_m
            arrays["net_income"][i, j] = r.net_income_m
            arrays["share_price"][i, j] = r.share_price
            arrays["dividend_per_share"][i, j] = r.dividend_per_share
            arrays["partner_bonus"][i, j] = r.partner_bonus_pool_m
            arrays["per_partner_comp"][i, j] = r.per_partner_total_comp_m
            arrays["working_capital"][i, j] = r.working_capital_m
            arrays["equity_value"][i, j] = r.equity_value_m
            arrays["enterprise_value"][i, j] = r.enterprise_value_m

    return arrays, input_params


def compute_percentiles(
    arrays: Dict[str, np.ndarray],
    percentiles: List[float] = [5, 25, 50, 75, 95],
) -> Dict[str, Dict[int, np.ndarray]]:
    """Compute percentile bands for each metric across years."""
    result = {}
    for metric, data in arrays.items():
        result[metric] = {}
        for p in percentiles:
            result[metric][p] = np.percentile(data, p, axis=0)
    return result


def compute_sensitivity(
    arrays: Dict[str, np.ndarray],
    input_params: Dict[str, np.ndarray],
    target_metric: str = "share_price",
    target_year: int = -1,
) -> List[Tuple[str, float]]:
    """
    Compute rank correlation between each input parameter and the target
    metric at the given year. Returns sorted list of (param, correlation).
    """
    from scipy import stats

    target = arrays[target_metric][:, target_year]
    correlations = []
    for param, values in input_params.items():
        corr, _ = stats.spearmanr(values, target)
        correlations.append((param, corr))

    correlations.sort(key=lambda x: abs(x[1]), reverse=True)
    return correlations


def print_mc_summary(
    arrays: Dict[str, np.ndarray],
    n_simulations: int,
    input_params: Dict[str, np.ndarray] = None,
):
    """Print Monte Carlo summary statistics."""
    pcts = compute_percentiles(arrays)
    n_years = arrays["revenue"].shape[1]

    print(f"\n{'='*100}")
    print(f"  MONTE CARLO SIMULATION — {n_simulations:,} iterations")
    print(f"{'='*100}")

    key_metrics = [
        ("Revenue ($M)", "revenue"),
        ("EBITDA ($M)", "ebitda"),
        ("Operating Margin", "operating_margin"),
        ("Share Price ($)", "share_price"),
        ("Dividend/Share ($)", "dividend_per_share"),
        ("Per-Partner Comp ($M)", "per_partner_comp"),
    ]

    for label, metric in key_metrics:
        print(f"\n  {label}")
        print(f"  {'Percentile':<12}" + "".join(f"{'Year '+str(y):>14}" for y in range(n_years)))
        print("  " + "-" * (12 + 14 * n_years))
        for p in [5, 25, 50, 75, 95]:
            vals = pcts[metric][p]
            if metric == "operating_margin":
                line = f"  {'P'+str(p):<12}" + "".join(f"{v*100:>13.1f}%" for v in vals)
            elif metric in ("share_price", "dividend_per_share"):
                line = f"  {'P'+str(p):<12}" + "".join(f"${v:>12.2f}" for v in vals)
            else:
                line = f"  {'P'+str(p):<12}" + "".join(f"${v:>12.1f}M" for v in vals)
            print(line)

    # Sensitivity analysis
    if input_params is not None:
        try:
            sensitivities = compute_sensitivity(arrays, input_params)
            print(f"\n  SENSITIVITY ANALYSIS (Rank correlation to Year 5 Share Price)")
            print(f"  {'-'*55}")
            for param, corr in sensitivities:
                bar_len = int(abs(corr) * 40)
                direction = "+" if corr > 0 else "-"
                bar = direction * bar_len
                print(f"  {param:<35} {corr:>+.3f}  {bar}")
        except ImportError:
            print("\n  (Install scipy for sensitivity analysis: pip install scipy)")


if __name__ == "__main__":
    n = 5000
    print(f"Running {n:,} Monte Carlo simulations...")
    arrays, input_params = run_monte_carlo(n_simulations=n)
    print_mc_summary(arrays, n, input_params)
