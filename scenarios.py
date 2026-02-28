"""
Scenario Analysis Module
========================
Defines bull, bear, and stress scenarios around the base case,
plus an AI disruption scenario for market studies risk.
"""

from dataclasses import replace
from typing import Dict, List, Tuple
from financial_model import ModelAssumptions, YearResult, run_model, print_summary


def define_scenarios() -> Dict[str, ModelAssumptions]:
    """Define named scenarios with modified assumptions."""
    base = ModelAssumptions()

    scenarios = {
        "Base Case": base,

        "Bull Case": replace(base,
            partner_growth_rate=0.06,           # 6% partner growth
            rpp_target_m=4.4,                    # Higher RPP target
            gross_margin_target_pct=0.57,        # Better margins
            operating_margin_target_pct=0.35,    # Strong operating leverage
        ),

        "Bear Case": replace(base,
            partner_growth_rate=0.02,           # Slower growth
            rpp_target_m=3.9,                    # Modest RPP improvement
            gross_margin_target_pct=0.53,        # Flat margins
            operating_margin_target_pct=0.27,    # Slight margin compression
        ),

        "AI Disruption": replace(base,
            partner_growth_rate=0.02,           # Growth slows
            rpp_target_m=3.5,                    # RPP declines from AI competition
            market_studies_pct=0.35,              # Market studies shrinks
            transformation_strategy_pct=0.65,    # Shift toward transformation
            gross_margin_target_pct=0.50,        # Margin pressure
            operating_margin_target_pct=0.25,    # Opex can't adjust fast enough
        ),

        "Rate Stress": replace(base,
            borrowing_rate=0.085,                # Rates spike
            structural_debt_m=130.0,             # More debt needed
            partner_growth_rate=0.03,            # Slightly slower growth
        ),
    }

    return scenarios


def run_all_scenarios() -> Dict[str, List[YearResult]]:
    """Run the model under all defined scenarios."""
    scenarios = define_scenarios()
    results = {}
    for name, assumptions in scenarios.items():
        results[name] = run_model(assumptions)
    return results


def compare_scenarios_table(all_results: Dict[str, List[YearResult]]):
    """Print a comparison of key metrics across scenarios at Year 5."""
    print(f"\n{'='*100}")
    print("  SCENARIO COMPARISON — Year 5 Outcomes")
    print(f"{'='*100}")

    col_w = 18
    scenarios = list(all_results.keys())

    header = f"{'Metric':<30}" + "".join(s.rjust(col_w) for s in scenarios)
    print(header)
    print("-" * len(header))

    def row(name, getter, fmt=".1f", prefix="$", suffix="M"):
        cells = [f"{name:<30}"]
        for s in scenarios:
            yr5 = all_results[s][-1]  # Last year
            v = getter(yr5)
            if suffix == "M":
                cells.append(f"{prefix}{v:{fmt}}{suffix}".rjust(col_w))
            elif suffix == "%":
                cells.append(f"{v*100:{fmt}}{suffix}".rjust(col_w))
            elif suffix == "":
                cells.append(f"{prefix}{v:{fmt}}".rjust(col_w))
            else:
                cells.append(f"{v:{fmt}}{suffix}".rjust(col_w))
        print("".join(cells))

    row("Revenue", lambda r: r.total_revenue_m)
    row("Gross Margin", lambda r: r.gross_margin_pct, suffix="%")
    row("Operating Profit", lambda r: r.operating_profit_m)
    row("Operating Margin", lambda r: r.operating_margin_pct, suffix="%")
    row("EBITDA", lambda r: r.ebitda_m)
    row("Share Price", lambda r: r.share_price, fmt=".2f", suffix="")
    row("Dividend/Share", lambda r: r.dividend_per_share, fmt=".2f", suffix="")
    row("Partner Comp ($M)", lambda r: r.per_partner_total_comp_m, fmt=".2f")
    row("Partners", lambda r: r.num_partners, fmt=".0f", prefix="", suffix="")
    print("-" * len(header))


if __name__ == "__main__":
    # Run and print each scenario
    all_results = run_all_scenarios()
    for name, results in all_results.items():
        print_summary(results, label=name)

    # Comparison table
    compare_scenarios_table(all_results)
