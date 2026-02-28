"""
Interactive Financial Dashboard — Flask Backend
================================================
Serves an interactive web UI for exploring assumptions, P&L, and cashflow.
"""

import json
from flask import Flask, request, jsonify, send_from_directory
from dataclasses import replace, asdict
from financial_model import ModelAssumptions, run_model

app = Flask(__name__, static_folder="static")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/defaults")
def defaults():
    """Return default assumptions."""
    a = ModelAssumptions()
    return jsonify({
        "num_partners": a.num_partners,
        "revenue_per_partner_m": a.revenue_per_partner_m,
        "partner_growth_rate": a.partner_growth_rate * 100,
        "rpp_target_m": a.rpp_target_m,
        "num_consulting_staff": a.num_consulting_staff,
        "gross_margin_pct": a.gross_margin_pct * 100,
        "gross_margin_target_pct": a.gross_margin_target_pct * 100,
        "operating_margin_pct": a.operating_margin_pct * 100,
        "operating_margin_target_pct": a.operating_margin_target_pct * 100,
        "partner_base_pay_k": a.partner_base_pay_k,
        "market_studies_pct": a.market_studies_pct * 100,
        "ebitda_fixed_pct": a.ebitda_fixed_pct * 100,
        "valuation_multiple": a.valuation_multiple,
        "structural_debt_m": a.structural_debt_m,
        "total_shares": a.total_shares,
        "investment_pct_revenue": a.investment_pct_revenue * 100,
        "working_capital_days": a.working_capital_days,
        "dividend_yield": a.dividend_yield * 100,
        "borrowing_rate": a.borrowing_rate * 100,
        "tax_rate": a.tax_rate * 100,
    })


@app.route("/api/calculate", methods=["POST"])
def calculate():
    """Run model with provided assumptions and return full results."""
    data = request.json or {}

    a = ModelAssumptions(
        num_partners=int(data.get("num_partners", 220)),
        revenue_per_partner_m=float(data.get("revenue_per_partner_m", 3.8)),
        partner_growth_rate=float(data.get("partner_growth_rate", 4)) / 100,
        rpp_target_m=float(data.get("rpp_target_m", 4.1)),
        num_consulting_staff=int(data.get("num_consulting_staff", 1400)),
        gross_margin_pct=float(data.get("gross_margin_pct", 53)) / 100,
        gross_margin_target_pct=float(data.get("gross_margin_target_pct", 55)) / 100,
        operating_margin_pct=float(data.get("operating_margin_pct", 28)) / 100,
        operating_margin_target_pct=float(data.get("operating_margin_target_pct", 32)) / 100,
        partner_base_pay_k=float(data.get("partner_base_pay_k", 380)),
        market_studies_pct=float(data.get("market_studies_pct", 50)) / 100,
        transformation_strategy_pct=1.0 - float(data.get("market_studies_pct", 50)) / 100,
        ebitda_fixed_pct=float(data.get("ebitda_fixed_pct", 6)) / 100,
        valuation_multiple=float(data.get("valuation_multiple", 6.25)),
        structural_debt_m=float(data.get("structural_debt_m", 100)),
        total_shares=int(data.get("total_shares", 100_000_000)),
        investment_pct_revenue=float(data.get("investment_pct_revenue", 2)) / 100,
        working_capital_days=int(data.get("working_capital_days", 120)),
        dividend_yield=float(data.get("dividend_yield", 8)) / 100,
        borrowing_rate=float(data.get("borrowing_rate", 6.5)) / 100,
        tax_rate=float(data.get("tax_rate", 21)) / 100,
    )

    results = run_model(a)

    years = []
    for r in results:
        implied_salary_k = (r.consulting_staff_cost_m * 1000) / r.num_consulting_staff if r.num_consulting_staff else 0

        # Cashflow statement
        cash_from_ops = r.net_income_m + r.depreciation_m
        wc_change = 0.0
        years.append({
            "year": r.year,
            # Revenue
            "num_partners": round(r.num_partners, 0),
            "revenue_per_partner_m": round(r.revenue_per_partner_m, 3),
            "total_revenue_m": round(r.total_revenue_m, 1),
            "market_studies_revenue_m": round(r.market_studies_revenue_m, 1),
            "transformation_revenue_m": round(r.transformation_revenue_m, 1),
            # CoS
            "partner_base_cost_m": round(r.partner_base_cost_m, 1),
            "consulting_staff_cost_m": round(r.consulting_staff_cost_m, 1),
            "other_cos_m": round(r.other_cos_m, 1),
            "total_cos_m": round(r.total_cos_m, 1),
            # Gross
            "gross_profit_m": round(r.gross_profit_m, 1),
            "gross_margin_pct": round(r.gross_margin_pct * 100, 1),
            # Opex
            "total_opex_m": round(r.total_opex_m, 1),
            "operating_profit_m": round(r.operating_profit_m, 1),
            "operating_margin_pct": round(r.operating_margin_pct * 100, 1),
            # EBITDA
            "ebitda_m": round(r.ebitda_m, 1),
            "partner_bonus_pool_m": round(r.partner_bonus_pool_m, 1),
            "total_partner_comp_m": round(r.total_partner_comp_m, 1),
            "per_partner_total_comp_m": round(r.per_partner_total_comp_m, 3),
            # Below the line
            "depreciation_m": round(r.depreciation_m, 1),
            "interest_expense_m": round(r.interest_expense_m, 1),
            "tax_m": round(r.tax_m, 1),
            "net_income_m": round(r.net_income_m, 1),
            # Valuation
            "enterprise_value_m": round(r.enterprise_value_m, 1),
            "equity_value_m": round(r.equity_value_m, 1),
            "share_price": round(r.share_price, 2),
            "dividend_per_share": round(r.dividend_per_share, 2),
            "total_dividends_m": round(r.total_dividends_m, 1),
            # Working capital & staff
            "working_capital_m": round(r.working_capital_m, 1),
            "capex_m": round(r.capex_m, 1),
            "num_consulting_staff": r.num_consulting_staff,
            "revenue_per_consultant_k": round(r.revenue_per_consultant_k, 0),
            "leverage_ratio": round(r.leverage_ratio, 1),
            "implied_salary_k": round(implied_salary_k, 0),
            # Cashflow
            "cash_from_ops_m": round(cash_from_ops, 1),
        })

    # Compute YoY working capital changes for cashflow
    for i in range(len(years)):
        if i == 0:
            years[i]["wc_change_m"] = 0.0
        else:
            years[i]["wc_change_m"] = round(
                years[i]["working_capital_m"] - years[i-1]["working_capital_m"], 1
            )
        years[i]["free_cash_flow_m"] = round(
            years[i]["cash_from_ops_m"] - years[i]["capex_m"] - years[i]["wc_change_m"], 1
        )

    return jsonify({"years": years})


if __name__ == "__main__":
    print("\n  Dashboard running at: http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
