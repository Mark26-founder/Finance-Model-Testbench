# Finance-Model-Testbench Fixture Corpus Documentation

## Overview

This directory contains the synthetic financial model fixture corpus generated for Phase C2 of **Finance-Model-Testbench**.

These fixtures serve as the deterministic ground-truth testbed for evaluating the testbench's ability to inspect workbooks, execute assertions, run controlled scenarios, and produce evidence in phases C3–C8.

## Fixture Inventory

### 1. Valid Fixture
- **Path**: `examples/fixtures/valid/valid_three_statement.xlsx`
- **Description**: A fully coherent synthetic 3-statement model containing Income Statement, Balance Sheet, and Cash Flow Statement.
- **Expected Ground-Truth Behavior**: All balance sheet identities, roll-forward schedules, and cross-statement links hold cleanly.

### 2. Defective Fixtures
- **BS Imbalance**: `examples/fixtures/defective/defective_balance_sheet_imbalance.xlsx`
  - *Defect*: Total Assets includes an unbacked `+50.0` offset (`STATEMENT_INTEGRITY`).
- **Retained Earnings Roll-Forward**: `examples/fixtures/defective/defective_retained_earnings_rollforward.xlsx`
  - *Defect*: Retained Earnings subtracts `100.0` for an unrecorded dividend (`ROLL_FORWARD`).
- **Cash Flow Linkage**: `examples/fixtures/defective/defective_cash_flow_linkage.xlsx`
  - *Defect*: Cash Flow Depreciation is hardcoded to `0.0` instead of linking to Income Statement (`CROSS_STATEMENT_LINK`).

### 3. Scenario-Capable Fixture
- **Path**: `examples/fixtures/scenarios/scenario_three_statement.xlsx`
- **Description**: Identical to the valid model but structured with explicit assumption inputs (`Revenue Growth`, `Operating Margin`, `Tax Rate`, `Interest Rate`, `Capex %`) on the `Assumptions` sheet.

## Manifest

The machine-readable ground truth for all fixtures is defined in:
`examples/fixtures/manifests/ground_truth_manifest.json`
