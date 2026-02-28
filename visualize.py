"""
Visualization Module
====================
Generates charts for the financial model, scenarios, and Monte Carlo output.
Saves charts as PNG files.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from typing import Dict, List

from financial_model import ModelAssumptions, YearResult, run_model
from scenarios import run_all_scenarios
from monte_carlo import run_monte_carlo, compute_percentiles


def setup_style():
    plt.rcParams.update({
        'figure.facecolor': 'white',
        'axes.facecolor': '#f8f9fa',
        'axes.grid': True,
        'grid.alpha': 0.3,
        'font.family': 'sans-serif',
        'font.size': 10,
    })


def plot_base_case(results: List[YearResult], output_dir: str = "."):
    """Generate base case financial charts."""
    setup_style()
    years = [r.year for r in results]

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("Base Case — 5 Year Financial Forecast", fontsize=14, fontweight='bold')

    # 1. Revenue waterfall
    ax = axes[0, 0]
    ax.bar(years, [r.total_revenue_m for r in results], color='#2F5496', alpha=0.8)
    ax.set_title("Total Revenue ($M)")
    ax.set_xlabel("Year")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}M'))

    # 2. Margin evolution
    ax = axes[0, 1]
    ax.plot(years, [r.gross_margin_pct * 100 for r in results], 'o-', label='Gross Margin', color='#2F5496', linewidth=2)
    ax.plot(years, [r.operating_margin_pct * 100 for r in results], 's-', label='Operating Margin', color='#C00000', linewidth=2)
    ax.set_title("Margin Evolution (%)")
    ax.set_xlabel("Year")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:.0f}%'))
    ax.legend()

    # 3. EBITDA & Partner Bonus
    ax = axes[0, 2]
    ax.bar(years, [r.ebitda_m for r in results], color='#2F5496', alpha=0.8, label='EBITDA')
    ax.bar(years, [r.partner_bonus_pool_m for r in results], color='#ED7D31', alpha=0.8, label='Partner Bonus')
    ax.set_title("EBITDA & Partner Bonus ($M)")
    ax.set_xlabel("Year")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}M'))
    ax.legend()

    # 4. Share Price
    ax = axes[1, 0]
    ax.plot(years, [r.share_price for r in results], 'o-', color='#2F5496', linewidth=2, markersize=8)
    ax.set_title("Share Price ($)")
    ax.set_xlabel("Year")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:.2f}'))
    ax.fill_between(years, [r.share_price for r in results], alpha=0.1, color='#2F5496')

    # 5. Dividend per Share
    ax = axes[1, 1]
    ax.bar(years, [r.dividend_per_share for r in results], color='#548235', alpha=0.8)
    ax.set_title("Dividend per Share ($)")
    ax.set_xlabel("Year")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:.2f}'))

    # 6. Cost breakdown stacked bar
    ax = axes[1, 2]
    ax.bar(years, [r.partner_base_cost_m for r in results], color='#2F5496', label='Partner Base')
    bottom1 = [r.partner_base_cost_m for r in results]
    ax.bar(years, [r.consulting_staff_cost_m for r in results], bottom=bottom1, color='#ED7D31', label='Consulting Staff')
    bottom2 = [b + r.consulting_staff_cost_m for b, r in zip(bottom1, results)]
    ax.bar(years, [r.other_cos_m for r in results], bottom=bottom2, color='#A5A5A5', label='Other CoS')
    bottom3 = [b + r.other_cos_m for b, r in zip(bottom2, results)]
    ax.bar(years, [r.total_opex_m for r in results], bottom=bottom3, color='#FFC000', label='OpEx')
    ax.set_title("Cost Structure ($M)")
    ax.set_xlabel("Year")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}M'))
    ax.legend(fontsize=8)

    plt.tight_layout()
    path = f"{output_dir}/base_case_charts.png"
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved {path}")


def plot_scenario_comparison(all_results: Dict[str, List[YearResult]], output_dir: str = "."):
    """Generate scenario comparison charts."""
    setup_style()

    scenarios = list(all_results.keys())
    colors = ['#2F5496', '#548235', '#ED7D31', '#C00000', '#7030A0']

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Scenario Comparison", fontsize=14, fontweight='bold')

    metrics = [
        ("Total Revenue ($M)", lambda r: r.total_revenue_m, axes[0, 0]),
        ("EBITDA ($M)", lambda r: r.ebitda_m, axes[0, 1]),
        ("Share Price ($)", lambda r: r.share_price, axes[1, 0]),
        ("Dividend/Share ($)", lambda r: r.dividend_per_share, axes[1, 1]),
    ]

    for label, getter, ax in metrics:
        for i, (name, results) in enumerate(all_results.items()):
            years = [r.year for r in results]
            vals = [getter(r) for r in results]
            ax.plot(years, vals, 'o-', label=name, color=colors[i % len(colors)], linewidth=2)
        ax.set_title(label)
        ax.set_xlabel("Year")
        ax.legend(fontsize=8)

    plt.tight_layout()
    path = f"{output_dir}/scenario_comparison.png"
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved {path}")


def plot_monte_carlo(arrays: Dict[str, np.ndarray], n_sims: int, output_dir: str = "."):
    """Generate Monte Carlo fan charts and histograms."""
    setup_style()
    pcts = compute_percentiles(arrays)
    n_years = arrays["revenue"].shape[1]
    years = list(range(n_years))

    # --- Fan charts ---
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle(f"Monte Carlo Simulation — {n_sims:,} Iterations", fontsize=14, fontweight='bold')

    fan_metrics = [
        ("Revenue ($M)", "revenue", axes[0, 0]),
        ("EBITDA ($M)", "ebitda", axes[0, 1]),
        ("Share Price ($)", "share_price", axes[0, 2]),
        ("Dividend/Share ($)", "dividend_per_share", axes[1, 0]),
        ("Per-Partner Comp ($M)", "per_partner_comp", axes[1, 1]),
        ("Operating Margin (%)", "operating_margin", axes[1, 2]),
    ]

    for label, metric, ax in fan_metrics:
        p5 = pcts[metric][5]
        p25 = pcts[metric][25]
        p50 = pcts[metric][50]
        p75 = pcts[metric][75]
        p95 = pcts[metric][95]

        if metric == "operating_margin":
            p5, p25, p50, p75, p95 = p5*100, p25*100, p50*100, p75*100, p95*100

        ax.fill_between(years, p5, p95, alpha=0.15, color='#2F5496', label='P5-P95')
        ax.fill_between(years, p25, p75, alpha=0.3, color='#2F5496', label='P25-P75')
        ax.plot(years, p50, 'o-', color='#2F5496', linewidth=2, label='Median')
        ax.set_title(label)
        ax.set_xlabel("Year")
        ax.legend(fontsize=8)

    plt.tight_layout()
    path = f"{output_dir}/monte_carlo_fans.png"
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved {path}")

    # --- Year 5 histograms ---
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle(f"Year 5 Distribution — {n_sims:,} Simulations", fontsize=14, fontweight='bold')

    hist_metrics = [
        ("Revenue ($M)", "revenue", axes[0, 0]),
        ("EBITDA ($M)", "ebitda", axes[0, 1]),
        ("Share Price ($)", "share_price", axes[0, 2]),
        ("Dividend/Share ($)", "dividend_per_share", axes[1, 0]),
        ("Per-Partner Comp ($M)", "per_partner_comp", axes[1, 1]),
        ("Equity Value ($M)", "equity_value", axes[1, 2]),
    ]

    for label, metric, ax in hist_metrics:
        data = arrays[metric][:, -1]
        ax.hist(data, bins=60, color='#2F5496', alpha=0.7, edgecolor='white')
        ax.axvline(np.median(data), color='#C00000', linestyle='--', linewidth=2, label=f'Median: {np.median(data):.1f}')
        ax.axvline(np.percentile(data, 5), color='#ED7D31', linestyle=':', linewidth=1.5, label=f'P5: {np.percentile(data, 5):.1f}')
        ax.axvline(np.percentile(data, 95), color='#ED7D31', linestyle=':', linewidth=1.5, label=f'P95: {np.percentile(data, 95):.1f}')
        ax.set_title(label)
        ax.legend(fontsize=8)

    plt.tight_layout()
    path = f"{output_dir}/monte_carlo_histograms.png"
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved {path}")


if __name__ == "__main__":
    from financial_model import run_model, ModelAssumptions
    from scenarios import run_all_scenarios
    from monte_carlo import run_monte_carlo

    print("Generating base case charts...")
    base_results = run_model(ModelAssumptions())
    plot_base_case(base_results)

    print("Generating scenario comparison...")
    all_results = run_all_scenarios()
    plot_scenario_comparison(all_results)

    print("Running Monte Carlo and generating charts...")
    arrays, _ = run_monte_carlo(n_simulations=5000)
    plot_monte_carlo(arrays, 5000)
