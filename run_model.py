#!/usr/bin/env python3
"""
Consulting Firm Financial Forecasting Model — Main Runner
==========================================================

Usage:
    python run_model.py              # Run everything
    python run_model.py --base       # Base case only
    python run_model.py --scenarios  # Scenarios only
    python run_model.py --mc         # Monte Carlo only
    python run_model.py --excel      # Generate Excel only
    python run_model.py --charts     # Generate charts only
    python run_model.py --mc-sims N  # Set Monte Carlo iterations (default 5000)
"""

import argparse
import sys
import time


def main():
    parser = argparse.ArgumentParser(description="Consulting Firm Financial Forecasting Model")
    parser.add_argument("--base", action="store_true", help="Run base case only")
    parser.add_argument("--scenarios", action="store_true", help="Run scenarios only")
    parser.add_argument("--mc", action="store_true", help="Run Monte Carlo only")
    parser.add_argument("--excel", action="store_true", help="Generate Excel workbook only")
    parser.add_argument("--charts", action="store_true", help="Generate charts only")
    parser.add_argument("--mc-sims", type=int, default=5000, help="Number of MC simulations")
    args = parser.parse_args()

    # If no specific flag, run everything
    run_all = not any([args.base, args.scenarios, args.mc, args.excel, args.charts])

    # --- Base Case ---
    if run_all or args.base:
        from financial_model import ModelAssumptions, run_model, print_summary
        print("\n" + "=" * 60)
        print("  STEP 1: BASE CASE FINANCIAL MODEL")
        print("=" * 60)
        assumptions = ModelAssumptions()
        results = run_model(assumptions)
        print_summary(results, "Base Case")

    # --- Scenarios ---
    if run_all or args.scenarios:
        from scenarios import run_all_scenarios, compare_scenarios_table
        from financial_model import print_summary
        print("\n" + "=" * 60)
        print("  STEP 2: SCENARIO ANALYSIS")
        print("=" * 60)
        all_results = run_all_scenarios()
        for name, results in all_results.items():
            print_summary(results, label=name)
        compare_scenarios_table(all_results)

    # --- Monte Carlo ---
    if run_all or args.mc:
        from monte_carlo import run_monte_carlo, print_mc_summary
        print("\n" + "=" * 60)
        print(f"  STEP 3: MONTE CARLO SIMULATION ({args.mc_sims:,} iterations)")
        print("=" * 60)
        t0 = time.time()
        arrays, input_params = run_monte_carlo(n_simulations=args.mc_sims)
        elapsed = time.time() - t0
        print(f"  Completed in {elapsed:.1f}s")
        print_mc_summary(arrays, args.mc_sims, input_params)

    # --- Charts ---
    if run_all or args.charts:
        from financial_model import ModelAssumptions, run_model
        from scenarios import run_all_scenarios
        from monte_carlo import run_monte_carlo
        from visualize import plot_base_case, plot_scenario_comparison, plot_monte_carlo
        print("\n" + "=" * 60)
        print("  STEP 4: GENERATING CHARTS")
        print("=" * 60)
        base_results = run_model(ModelAssumptions())
        plot_base_case(base_results)

        all_results = run_all_scenarios()
        plot_scenario_comparison(all_results)

        if not (run_all or args.mc):
            arrays, _ = run_monte_carlo(n_simulations=args.mc_sims)
        plot_monte_carlo(arrays, args.mc_sims)

    # --- Excel ---
    if run_all or args.excel:
        from export_excel import export_to_excel
        print("\n" + "=" * 60)
        print("  STEP 5: GENERATING EXCEL WORKBOOK")
        print("=" * 60)
        export_to_excel(n_mc_sims=args.mc_sims)

    print("\n" + "=" * 60)
    print("  COMPLETE")
    print("=" * 60)
    print("\nOutputs:")
    if run_all or args.excel:
        print("  - consulting_firm_forecast.xlsx  (Full spreadsheet model)")
    if run_all or args.charts:
        print("  - base_case_charts.png           (Base case visualizations)")
        print("  - scenario_comparison.png        (Scenario comparison)")
        print("  - monte_carlo_fans.png           (MC fan charts)")
        print("  - monte_carlo_histograms.png     (MC Year 5 distributions)")


if __name__ == "__main__":
    main()
