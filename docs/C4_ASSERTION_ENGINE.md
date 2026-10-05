# C4 — Deterministic Financial Test Engine

## Overview

The C4 Assertion Engine evaluates **explicit financial conditions** against values
already available through the C3 workbook inspection layer.

It answers a single deterministic question:

> Does this explicitly defined financial condition hold, within its declared tolerance?

The engine is **stateless**, **reproducible**, and **local-first**.
It does not recalculate formulas, access the network, or use an LLM.

---

## Architecture Position

```text
Workbook (.xlsx)
      ↓
C3 — WorkbookInspector  →  WorkbookInspectionResult
      ↓
C4 — AssertionEngine    →  List[AssertionResult]
      ↓
C5 — Scenario Execution (NOT YET IMPLEMENTED)
      ↓
C6 — Evidence / Reporting (NOT YET IMPLEMENTED)
```

---

## Assertion Model

### CellReference

An explicit pointer to a workbook/sheet/cell coordinate.

```python
CellReference(
    sheet_name="Balance Sheet",
    coordinate="C5",
    label="Total Assets (Current)"  # optional, for reporting only
)
```

The engine never infers financial meaning from sheet names, row positions,
cell colours, or formatting.  Only the coordinate matters.

---

### ToleranceSpec

Every assertion declares an explicit tolerance.

```python
exact_tolerance()                  # Python == equality
absolute_tolerance(0.01)           # abs(observed - expected) <= 0.01
relative_tolerance(0.001,          # abs(observed - expected) /
                  min_reference=1.0)  #   max(abs(expected), 1.0) <= 0.001
```

**No hidden defaults.**  Tolerance must be stated in every TestDefinition.

Edge case: when `expected == 0`, RELATIVE tolerance uses `min_reference` as
the denominator guard to prevent division by zero.

---

### AssertionType

| Type | Relationship | Required operands |
|------|-------------|-------------------|
| `EQUALITY` | `A == B` | Exactly 2 |
| `DIFFERENCE` | `A - B == expected_value` | Exactly 2 |
| `SUM_EQUALITY` | `sum(A, B, C, …) == expected_value` | 2 or more |

---

### TestDefinition

A single, self-contained assertion specification.

```python
TestDefinition(
    test_id="TD_BS_001",
    description="Balance Sheet identity: Total Assets == Total Liabilities + Equity",
    assertion_type=AssertionType.EQUALITY,
    operands=[
        CellReference("Balance Sheet", "C5", label="Total Assets"),
        CellReference("Balance Sheet", "C12", label="Total Liabilities + Equity"),
    ],
    tolerance=absolute_tolerance(0.01),
)
```

Financial examples:

```python
# Assets = Liabilities + Equity
TestDefinition(
    test_id="BS_IDENTITY",
    description="Balance sheet balances",
    assertion_type=AssertionType.EQUALITY,
    operands=[
        CellReference("Balance Sheet", "C5"),   # Total Assets
        CellReference("Balance Sheet", "C12"),  # Total L+E
    ],
    tolerance=absolute_tolerance(0.01),
)

# Retained Earnings roll-forward: Ending = Beginning + Net Income
TestDefinition(
    test_id="RE_ROLLFORWARD",
    description="Retained Earnings roll-forward",
    assertion_type=AssertionType.DIFFERENCE,
    operands=[
        CellReference("Balance Sheet", "C10"),  # Ending RE
        CellReference("Balance Sheet", "B10"),  # Beginning RE
    ],
    expected_value=...,  # Net Income value from Income Statement
    tolerance=absolute_tolerance(0.01),
)

# Depreciation cross-statement: CF add-back == IS depreciation
TestDefinition(
    test_id="DEPR_LINK",
    description="Depreciation linkage IS → CF",
    assertion_type=AssertionType.EQUALITY,
    operands=[
        CellReference("Cash Flow Statement", "B3"),  # CF Depreciation
        CellReference("Income Statement", "C5"),      # IS Depreciation
    ],
    tolerance=absolute_tolerance(0.01),
)
```

---

## Assertion Engine

```python
from finance_model_testbench import (
    WorkbookInspector,
    AssertionEngine,
    TestDefinition,
    AssertionType,
    CellReference,
    absolute_tolerance,
)

inspector = WorkbookInspector()
inspection = inspector.inspect("path/to/model.xlsx")

engine = AssertionEngine()
results = engine.run(inspection, [td1, td2, td3])

for result in results:
    print(result.test_id, result.status.value, result.message)
```

The engine returns one `AssertionResult` per `TestDefinition`, in input order.

---

## Value Resolution

The engine resolves each `CellReference` against the `WorkbookInspectionResult`.

| Cell state | `ResolvedValueKind` | `is_usable` |
|-----------|---------------------|-------------|
| Plain numeric | `NUMERIC` | ✓ |
| Formula with openpyxl cached numeric | `FORMULA_CACHED` | ✓ |
| Formula with no usable cached value | `FORMULA_NO_CACHE` | ✗ |
| Non-numeric (string, bool) | `NON_NUMERIC` | ✗ |
| Sheet or cell not found | `MISSING` | ✗ |

**Blank/missing cells are never silently coerced to zero.**

**Strings are never silently coerced to numbers.**

---

## Result Statuses

| Status | Meaning |
|--------|---------|
| `PASS` | Condition evaluated; assertion satisfied |
| `FAIL` | Condition evaluated; assertion **not** satisfied |
| `ERROR` | Unexpected engine-level failure; or required configuration missing |
| `UNSUPPORTED` | Assertion type or value kind is outside current engine scope |
| `INCOMPLETE` | Required value unavailable (e.g. formula with no cache); **≠ FAIL** |

### Critical distinction: INCOMPLETE ≠ FAIL

A formula cell with no cached value cannot be evaluated.
The engine returns `INCOMPLETE`, not `FAIL`.

This distinction matters because a freshly generated workbook (from code) will
have formula cells but no Excel-calculated cached values.  The engine must not
claim a defect exists merely because recalculation has not occurred.

`INCOMPLETE` means: _"I could not evaluate this; run C5 recalculation and retry."_

---

## AssertionResult

Every executed assertion produces:

```python
AssertionResult(
    test_id="TD_BS_001",
    status=AssertionStatus.FAIL,
    assertion_type=AssertionType.EQUALITY,
    expected=1012.5,
    observed=1062.5,
    difference=50.0,
    tolerance=ToleranceSpec(tolerance_type=ToleranceType.ABSOLUTE, tolerance_value=0.01, ...),
    resolved=[ResolvedValue(...), ResolvedValue(...)],
    message="FAIL: 'Balance Sheet'!C5 = 1062.5 ≠ 'Balance Sheet'!C12 = 1012.5 ..."
)
```

All results are JSON-serializable via `.to_dict()`.

---

## Calculation Boundary

C4 does **not** implement:

- Excel formula evaluation
- Python-based spreadsheet recalculation
- xlcalculator, pycel, or LibreOffice
- Any formula execution engine

The engine uses only values already stored in the `WorkbookInspectionResult`.

For formula cells, openpyxl provides the value cached by Excel at the time the
workbook was last saved.  This cached value is used **as-is** and is clearly
labelled `FORMULA_CACHED` in the result.

If a required value is unavailable, the engine returns `INCOMPLETE`.

**Formula recalculation is deferred to C5.**

---

## Security

The assertion engine:

- Makes no network calls
- Executes no workbook macros
- Executes no arbitrary code
- Reads only from the explicitly supplied `WorkbookInspectionResult`
- Never modifies source workbooks

---

## Determinism

Given identical `WorkbookInspectionResult` and identical `TestDefinition` inputs,
the engine always produces identical `AssertionResult` outputs.

Result ordering matches the input definition order.

---

## Limitations

1. **Formula cells without cached values return `INCOMPLETE`**, not `PASS` or `FAIL`.
   Freshly generated workbooks (e.g. from code) typically have no cached values.
   This is expected behaviour.  C5 recalculation will address this.

2. **openpyxl cached values may be stale** if the workbook was not recalculated before
   saving.  `FORMULA_CACHED` results carry a note about this provenance.

3. **Only `.xlsx` workbooks are supported** (inherited from C3).

4. **No cross-workbook assertions** in the current implementation.

5. **The engine does not infer financial relationships** from cell position, colour,
   or formatting.  All relationships must be explicitly stated in `TestDefinition`.

---

## Supported Files

```text
src/finance_model_testbench/assertion_models.py  — Data model
src/finance_model_testbench/assertion_engine.py  — Engine
src/finance_model_testbench/exceptions.py        — Exception hierarchy (C4 additions)
tests/test_assertion_engine.py                   — C4 test suite
```
