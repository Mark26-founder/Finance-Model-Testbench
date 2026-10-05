# Defect Taxonomy — Finance-Model-Testbench C2

This document defines the defect classification hierarchy used by Finance-Model-Testbench fixtures and benchmark sets.

## Defect Categories

### 1. STATEMENT_INTEGRITY
- **Definition**: Violations of core accounting balance identities within a single financial statement or report.
- **Example**: `Balance Sheet Total Assets ≠ Total Liabilities + Equity`.
- **Target Detection**: Balance sheet balance checks, total row/column verification.

### 2. ROLL_FORWARD
- **Definition**: Discrepancies in schedule roll-forwards where `Ending Balance` does not equal `Beginning Balance + Additions - Reductions`.
- **Example**: Retained Earnings ending balance formula omitting Net Income or miscalculating dividend reductions.
- **Target Detection**: Roll-forward schedule assertions (Retained Earnings, Debt, Fixed Assets, Cash).

### 3. CROSS_STATEMENT_LINK
- **Definition**: Broken formula links where values that must match across statements differ due to missing links, hardcoded overrides, or incorrect cell references.
- **Example**: Depreciation on the Cash Flow Statement hardcoded to `0` instead of linking to Depreciation on the Income Statement.
- **Target Detection**: Cross-statement consistency assertions (IS -> CF, IS -> BS, BS -> CF).

### 4. SCENARIO_BEHAVIOUR
- **Definition**: Failures of assumption propagation where changes in input assumption cells do not propagate directionally or mathematically to output items.
- **Example**: Changing Revenue Growth Rate assumption does not alter Income Statement Revenue.
- **Target Detection**: Scenario execution assertion evaluation.

---

## Fixture Defect Mapping

| Fixture Path | Defect Category | Affected Cells | Expected Relationship | Intentionally Incorrect Relationship |
|---|---|---|---|---|
| `examples/fixtures/defective/defective_balance_sheet_imbalance.xlsx` | `STATEMENT_INTEGRITY` | `'Balance Sheet'!C5` | `Assets = Liabilities + Equity` | `Assets = Liabilities + Equity + 50.0` |
| `examples/fixtures/defective/defective_retained_earnings_rollforward.xlsx` | `ROLL_FORWARD` | `'Balance Sheet'!C10` | `Ending RE = Prior RE + Net Income` | `Ending RE = Prior RE + Net Income - 100.0` |
| `examples/fixtures/defective/defective_cash_flow_linkage.xlsx` | `CROSS_STATEMENT_LINK` | `'Cash Flow Statement'!C3` | `CF Depreciation = IS Depreciation` | `CF Depreciation = 0.0` (Hardcoded) |
