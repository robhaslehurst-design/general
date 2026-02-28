"""
Financial Forecasting Model for a Management Consulting Firm
=============================================================
Core model engine with P&L, balance sheet metrics, and valuation.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ModelAssumptions:
    """All input assumptions for the financial model."""

    # --- Base Year (Year 0) ---
    num_partners: int = 220
    revenue_per_partner_m: float = 3.8  # $M per partner per year
    num_consulting_staff: int = 1400
    gross_margin_pct: float = 0.53
    operating_margin_pct: float = 0.28

    # --- Growth assumptions (5-year horizon) ---
    partner_growth_rate: float = 0.04  # 4% p.a.
    rpp_target_m: float = 4.1  # RPP in Year 5 ($M)
    forecast_years: int = 5

    # --- Gross margin cost structure ---
    partner_base_pay_k: float = 380  # $K per partner
    # Consulting staff salary is derived to reconcile gross margin

    # --- Margin trajectory ---
    gross_margin_target_pct: float = 0.55  # slight improvement
    operating_margin_target_pct: float = 0.32  # operating leverage

    # --- Business mix ---
    market_studies_pct: float = 0.50  # AI substitution risk
    transformation_strategy_pct: float = 0.50

    # --- EBITDA & valuation ---
    ebitda_fixed_pct: float = 0.06  # 6% of revenue
    ebitda_residual_share: float = 1 / 3  # 1/3 of (OP - 6% rev)
    # Partner bonus pool = 2/3 of (OP - 6% rev)

    valuation_multiple: float = 6.25  # EV = 6.25x EBITDA
    structural_debt_m: float = 100.0  # $M
    total_shares: int = 100_000_000  # 100M shares

    # --- Capital & working capital ---
    investment_pct_revenue: float = 0.02  # 2% of revenue
    working_capital_days: int = 120
    dividend_yield: float = 0.08  # 8% of equity value
    borrowing_rate: float = 0.065  # 6.5%
    tax_rate: float = 0.21  # US corporate tax rate

    # --- Depreciation assumption ---
    # Capex depreciates over 5 years straight-line
    depreciation_life: int = 5


@dataclass
class YearResult:
    """Financial results for a single year."""
    year: int

    # Revenue build-up
    num_partners: float
    revenue_per_partner_m: float
    total_revenue_m: float

    # Revenue mix
    market_studies_revenue_m: float
    transformation_revenue_m: float

    # Cost of sales / Gross profit
    partner_base_cost_m: float
    consulting_staff_cost_m: float
    other_cos_m: float
    total_cos_m: float
    gross_profit_m: float
    gross_margin_pct: float

    # Operating expenses
    total_opex_m: float
    operating_profit_m: float
    operating_margin_pct: float

    # EBITDA & partner economics
    ebitda_m: float
    partner_bonus_pool_m: float
    total_partner_comp_m: float  # base + bonus
    per_partner_total_comp_m: float

    # Below the line
    depreciation_m: float
    capex_m: float
    interest_expense_m: float
    tax_m: float
    net_income_m: float

    # Valuation
    enterprise_value_m: float
    equity_value_m: float
    share_price: float
    dividend_per_share: float
    total_dividends_m: float

    # Working capital
    working_capital_m: float

    # Staff metrics
    num_consulting_staff: int
    revenue_per_consultant_k: float
    leverage_ratio: float  # consultants per partner


def run_model(assumptions: ModelAssumptions) -> List[YearResult]:
    """Run the financial model for the forecast period.

    Returns a list of YearResult objects for Year 0 through Year N.
    """
    a = assumptions
    results = []

    # Pre-calculate RPP growth path (linear interpolation to target)
    rpp_base = a.revenue_per_partner_m
    rpp_annual_increase = (a.rpp_target_m - rpp_base) / a.forecast_years

    # Pre-calculate margin trajectories (linear ramp)
    gm_annual_increase = (a.gross_margin_target_pct - a.gross_margin_pct) / a.forecast_years
    om_annual_increase = (a.operating_margin_target_pct - a.operating_margin_pct) / a.forecast_years

    # Derive consulting staff salary from Year 0 reconciliation
    base_revenue = a.num_partners * a.revenue_per_partner_m  # $M
    base_cos = base_revenue * (1 - a.gross_margin_pct)
    base_partner_cost = a.num_partners * a.partner_base_pay_k / 1000  # $M
    base_consulting_staff_cost = base_cos - base_partner_cost
    avg_consultant_salary_k = (base_consulting_staff_cost * 1000) / a.num_consulting_staff

    # Track cumulative capex for depreciation
    capex_history = []

    # Base leverage ratio (consultants per partner)
    base_leverage = a.num_consulting_staff / a.num_partners

    for yr in range(a.forecast_years + 1):
        # --- Partners & Revenue ---
        partners = a.num_partners * (1 + a.partner_growth_rate) ** yr
        rpp = rpp_base + rpp_annual_increase * yr
        revenue = partners * rpp

        # Revenue mix
        market_studies_rev = revenue * a.market_studies_pct
        transformation_rev = revenue * a.transformation_strategy_pct

        # --- Target margins for this year ---
        target_gm = a.gross_margin_pct + gm_annual_increase * yr
        target_om = a.operating_margin_pct + om_annual_increase * yr

        # --- Cost of Sales ---
        # Total CoS is driven by target gross margin
        target_cos = revenue * (1 - target_gm)
        partner_base_cost = partners * a.partner_base_pay_k / 1000

        # Consulting staff grows proportionally with partners (maintain leverage)
        consulting_staff = int(round(a.num_consulting_staff * (1 + a.partner_growth_rate) ** yr))

        # Consulting staff cost is the residual after partner base, within total CoS envelope
        # This implicitly captures productivity gains needed for margin improvement
        consulting_cost = max(0, target_cos - partner_base_cost)
        # Any surplus beyond consulting cost is other CoS (zero in well-calibrated model)
        other_cos = 0.0

        total_cos = partner_base_cost + consulting_cost + other_cos
        gross_profit = revenue - total_cos
        actual_gm = gross_profit / revenue if revenue > 0 else 0

        # --- Operating Expenses ---
        target_opex = gross_profit - (revenue * target_om)
        total_opex = max(0, target_opex)
        operating_profit = gross_profit - total_opex
        actual_om = operating_profit / revenue if revenue > 0 else 0

        # --- EBITDA ---
        ebitda_base = revenue * a.ebitda_fixed_pct
        residual = max(0, operating_profit - ebitda_base)
        ebitda = ebitda_base + residual * a.ebitda_residual_share
        partner_bonus = residual * (1 - a.ebitda_residual_share)  # 2/3

        total_partner_comp = partner_base_cost + partner_bonus
        per_partner_comp = total_partner_comp / partners if partners > 0 else 0

        # --- Capex & Depreciation ---
        capex = revenue * a.investment_pct_revenue
        capex_history.append(capex)

        # Depreciation: straight-line over depreciation_life years
        depreciation = 0.0
        for past_yr, past_capex in enumerate(capex_history):
            age = yr - past_yr
            if age < a.depreciation_life:
                depreciation += past_capex / a.depreciation_life

        # --- Interest & Tax ---
        interest = a.structural_debt_m * a.borrowing_rate
        pre_tax_income = ebitda - depreciation - interest
        tax = max(0, pre_tax_income * a.tax_rate)
        net_income = pre_tax_income - tax

        # --- Valuation ---
        ev = ebitda * a.valuation_multiple
        equity_value = max(0, ev - a.structural_debt_m)
        # Convert $M to $ for per-share calculations
        share_price = (equity_value * 1e6) / a.total_shares if a.total_shares > 0 else 0

        # --- Dividends ---
        total_dividends = equity_value * a.dividend_yield
        dividend_per_share = (total_dividends * 1e6) / a.total_shares if a.total_shares > 0 else 0

        # --- Working Capital ---
        working_capital = revenue * (a.working_capital_days / 365)

        # --- Staff Metrics ---
        rev_per_consultant = (revenue * 1000) / consulting_staff if consulting_staff > 0 else 0
        leverage = consulting_staff / partners if partners > 0 else 0

        results.append(YearResult(
            year=yr,
            num_partners=partners,
            revenue_per_partner_m=rpp,
            total_revenue_m=revenue,
            market_studies_revenue_m=market_studies_rev,
            transformation_revenue_m=transformation_rev,
            partner_base_cost_m=partner_base_cost,
            consulting_staff_cost_m=consulting_cost,
            other_cos_m=other_cos,
            total_cos_m=total_cos,
            gross_profit_m=gross_profit,
            gross_margin_pct=actual_gm,
            total_opex_m=total_opex,
            operating_profit_m=operating_profit,
            operating_margin_pct=actual_om,
            depreciation_m=depreciation,
            capex_m=capex,
            interest_expense_m=interest,
            tax_m=tax,
            net_income_m=net_income,
            ebitda_m=ebitda,
            partner_bonus_pool_m=partner_bonus,
            total_partner_comp_m=total_partner_comp,
            per_partner_total_comp_m=per_partner_comp,
            enterprise_value_m=ev,
            equity_value_m=equity_value,
            share_price=share_price,
            dividend_per_share=dividend_per_share,
            total_dividends_m=total_dividends,
            working_capital_m=working_capital,
            num_consulting_staff=consulting_staff,
            revenue_per_consultant_k=rev_per_consultant,
            leverage_ratio=leverage,
        ))

    return results


def print_summary(results: List[YearResult], label: str = "Base Case"):
    """Print a formatted summary table."""
    print(f"\n{'='*90}")
    print(f"  {label}")
    print(f"{'='*90}")

    headers = ["Metric"] + [f"Year {r.year}" for r in results]
    col_w = 14

    def row(name, values, fmt=".1f", prefix="$", suffix="M"):
        cells = [f"{name:<32}"]
        for v in values:
            if suffix == "M":
                cells.append(f"{prefix}{v:{fmt}}{suffix}".rjust(col_w))
            elif suffix == "%":
                cells.append(f"{v*100:{fmt}}{suffix}".rjust(col_w))
            elif suffix == "":
                cells.append(f"{prefix}{v:{fmt}}{suffix}".rjust(col_w))
            else:
                cells.append(f"{v:{fmt}}{suffix}".rjust(col_w))
        print("".join(cells))

    def separator():
        print("-" * (32 + col_w * len(results)))

    separator()
    print("".join([f"{'Metric':<32}"] + [f"Year {r.year}".rjust(col_w) for r in results]))
    separator()

    print("\n  REVENUE BUILD-UP")
    row("Partners (#)", [r.num_partners for r in results], ".0f", "", "")
    row("Revenue/Partner ($M)", [r.revenue_per_partner_m for r in results], ".2f")
    row("Total Revenue", [r.total_revenue_m for r in results])
    row("  Market Studies", [r.market_studies_revenue_m for r in results])
    row("  Transformation/Strategy", [r.transformation_revenue_m for r in results])

    print("\n  COST OF SALES")
    row("Partner Base Cost", [r.partner_base_cost_m for r in results])
    row("Consulting Staff Cost", [r.consulting_staff_cost_m for r in results])
    row("Other CoS", [r.other_cos_m for r in results])
    separator()
    row("Gross Profit", [r.gross_profit_m for r in results])
    row("Gross Margin", [r.gross_margin_pct for r in results], ".1f", "", "%")

    print("\n  OPERATING EXPENSES")
    row("Total OpEx", [r.total_opex_m for r in results])
    separator()
    row("Operating Profit", [r.operating_profit_m for r in results])
    row("Operating Margin", [r.operating_margin_pct for r in results], ".1f", "", "%")

    print("\n  EBITDA & PARTNER ECONOMICS")
    row("EBITDA", [r.ebitda_m for r in results])
    row("Partner Bonus Pool", [r.partner_bonus_pool_m for r in results])
    row("Total Partner Comp", [r.total_partner_comp_m for r in results])
    row("Per Partner Comp ($M)", [r.per_partner_total_comp_m for r in results], ".2f")

    print("\n  BELOW THE LINE")
    row("Depreciation", [r.depreciation_m for r in results])
    row("Interest Expense", [r.interest_expense_m for r in results])
    row("Tax", [r.tax_m for r in results])
    row("Net Income", [r.net_income_m for r in results])

    print("\n  VALUATION")
    row("Enterprise Value", [r.enterprise_value_m for r in results])
    row("Equity Value", [r.equity_value_m for r in results])
    row("Share Price ($)", [r.share_price for r in results], ".2f", "$", "")
    row("Dividend/Share ($)", [r.dividend_per_share for r in results], ".2f", "$", "")
    row("Total Dividends", [r.total_dividends_m for r in results])

    print("\n  WORKING CAPITAL & STAFF")
    row("Working Capital", [r.working_capital_m for r in results])
    row("Capex (Investment)", [r.capex_m for r in results])
    row("Consulting Staff (#)", [r.num_consulting_staff for r in results], ".0f", "", "")
    row("Rev/Consultant ($K)", [r.revenue_per_consultant_k for r in results], ".0f", "$", "")
    row("Leverage (Staff/Partner)", [r.leverage_ratio for r in results], ".1f", "", "x")
    separator()


if __name__ == "__main__":
    assumptions = ModelAssumptions()
    results = run_model(assumptions)
    print_summary(results)
