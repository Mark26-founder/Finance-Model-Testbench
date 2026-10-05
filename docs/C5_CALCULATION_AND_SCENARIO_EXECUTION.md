# C5 — Calculation and Scenario Execution

## Overview

The C5 Scenario Execution layer extends the deterministic assertion engine (C4) by introducing **local formula recalculation** and **controlled assumption changes (scenarios)**.

It answers two fundamental testing questions:

1. > *When all formulas in a model are freshly recalculated, do explicit financial assertions hold?*
2. > *When key model assumptions change, does the model recalculate consistently and satisfy expected financial conditions?*

The system remains **local-first**, **reproducible**, **stateless**, and **security-conscious**.

---

## Architecture Position

```text
Source Workbook (.xlsx)
      ↓ (Byte SHA-256 Hash Recorded)
Isolated Temp Workspace
      ↓
Scenario Inputs Applied (openpyxl)
      ↓
Formula Graph Recalculated (xlcalculator)
      ↓
WorkbookInspectionResult (Freshly Recalculated Values)
      ↓
C4 Assertion Engine → List[AssertionResult]
      ↓
Source SHA-256 Verified (Byte Immutability Confirmed)
      ↓
ScenarioExecutionResult
```

---

## Recalculation Engine Selection (`xlcalculator`)

Formula recalculation is handled locally by `xlcalculator` (v0.5.0+):

* **Pure Python**: Runs locally without requiring Microsoft Excel, COM automation, or external services.
* **Deterministic**: Compiles workbook formulas into an in-memory dependency DAG.
* **Tested Scope**: Successfully evaluates synthetic 3-statement financial models, including cross-statement link formulas (`Income Statement`, `Balance Sheet`, `Cash Flow Statement`).
* **Unwrapped Values**: Automatically unwraps custom xlcalculator types (`Number`) to native Python numeric primitives (`float`, `int`).

---

## Source Workbook Immutability & Scenario Isolation

1. **Byte-Level Source Immutability**: The original `.xlsx` file is never opened in write mode. A SHA-256 hash is taken before execution and verified after execution.
2. **Safe Isolation**: Every scenario runs inside an isolated temporary directory using a copy of the source workbook.
3. **No Cross-Contamination**: Independent scenarios start from a clean copy of the original workbook. Scenario inputs never leak between runs.
4. **Exception-Safe Cleanup**: Temporary files are deleted in `finally` blocks regardless of execution outcome.

---

## Data Model

### `ScenarioInput`

Represents a single assumption change target.

```python
ScenarioInput(
    cell=CellReference("Assumptions", "B2"),
    value=0.10,
    label="Revenue Growth Rate (10%)"
)
```

### `ScenarioDefinition`

Groups a set of assumption changes for a test run.

```python
ScenarioDefinition(
    scenario_id="SCEN_REV_10",
    description="Test model balance under 10% revenue growth assumption",
    inputs=(
        ScenarioInput(CellReference("Assumptions", "B2"), 0.10),
    )
)
```

### `ScenarioExecutionResult`

Structured outcome of executing a scenario against a test suite.

```python
ScenarioExecutionResult(
    scenario_id="SCEN_REV_10",
    source_file="/path/to/model.xlsx",
    source_sha256="a1b2c3...",
    recalculation_status=RecalculationStatus.SUCCESS,
    recalculation_message="Recalculation completed successfully.",
    assertion_results=(...),
    inputs_applied={"'Assumptions'!B2": "0.10"}
)
```

---

## Recalculation Status Semantics

* `SUCCESS`: All formula cells evaluated successfully without engine or calculation errors.
* `ERROR`: One or more formula cells encountered evaluation errors (`#REF!`, `#DIV/0!`, missing references).
* `UNSUPPORTED`: The workbook feature or formula function is outside `xlcalculator` parser capabilities.
* `INCOMPLETE`: Required cells lack formula definitions or input values.

---

## Code Example

```python
from finance_model_testbench import (
    ScenarioRunner,
    ScenarioDefinition,
    ScenarioInput,
    TestDefinition,
    AssertionType,
    CellReference,
    absolute_tolerance,
)

runner = ScenarioRunner()

test_def = TestDefinition(
    test_id="TD_BS_BALANCE",
    description="Assets == Liabilities + Equity",
    assertion_type=AssertionType.EQUALITY,
    operands=[
        CellReference("Balance Sheet", "C5"),
        CellReference("Balance Sheet", "C12"),
    ],
    tolerance=absolute_tolerance(0.01),
)

scenario = ScenarioDefinition(
    scenario_id="SCEN_GROWTH_TEST",
    description="Test 10% Revenue Growth",
    inputs=[ScenarioInput(CellReference("Assumptions", "B2"), 0.10)],
)

result = runner.run("path/to/model.xlsx", [test_def], scenario=scenario)

print(f"Scenario: {result.scenario_id}")
print(f"Recalculation: {result.recalculation_status.value}")
for a_res in result.assertion_results:
    print(f"[{a_res.status.value}] {a_res.message}")
```

---

## Supported Files

```text
src/finance_model_testbench/scenario_models.py — Scenario & recalculation data model
src/finance_model_testbench/recalculator.py      — xlcalculator wrapper & inspection updater
src/finance_model_testbench/scenario_runner.py   — Isolation & scenario pipeline runner
tests/test_scenario_runner.py                    — C5 test suite (14 tests)
docs/C5_CALCULATION_AND_SCENARIO_EXECUTION.md    — C5 architecture documentation
```
