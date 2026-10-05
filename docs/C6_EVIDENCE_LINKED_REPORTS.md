# C6 — Evidence-Linked Reports

## Overview

The C6 Evidence-Linked Reporting Layer transforms C4 assertion results and C5 scenario execution results into structured, deterministic, machine-readable JSON reports and human-readable Markdown reports.

The central design principle is:

> **Every reported outcome must be directly traceable to the underlying evidence (workbook SHA-256, cell coordinates, scenario inputs, expected vs observed values, and numerical tolerances).**

The reporting layer does **not** recalculate financial values, reinterpret assertion logic, or alter per-assertion statuses.

---

## Architecture Position

```text
C5 ScenarioRunner → ScenarioExecutionResult + List[TestDefinition]
      ↓
C6 ReportGenerator → TestbenchReport
      ↓                      ↓
.to_json()               .to_markdown()
(Deterministic JSON)     (Human-Readable Markdown)
```

---

## Output Formats

1. **JSON (`to_json()`):** Mandatory, deterministic, machine-readable format. Preserves exact floating-point precision without pre-rounding.
2. **Markdown (`to_markdown()`):** Clean, human-readable summary table and detailed evidence blocks. Sanitizes user strings to prevent Markdown formatting injection attacks.

---

## Data Model & Schema

### `ReportMetadata`

* `schema_version`: Version string (`"1.0.0"`).
* `report_id`: Deterministic 16-character hex hash derived from `source_sha256`, `scenario_id`, and sorted `test_ids`.
* `source_filename`: Basename of the target workbook file (e.g. `valid_three_statement.xlsx`). Absolute paths are omitted to prevent machine-path exposure.
* `source_sha256`: SHA-256 byte hash of the target workbook file.
* `scenario_id`: Identifier of the executed scenario (`"BASELINE"` if none).
* `inputs_applied`: Dictionary of applied scenario inputs.
* `timestamp`: Optional timestamp string (defaults to `None` for byte-level output determinism).

### `ReportSummary`

* `total_assertions`: Total number of assertions evaluated.
* `pass_count`, `fail_count`, `error_count`, `unsupported_count`, `incomplete_count`: Metric breakdown by status.
* `overall_outcome`: Single overall execution status (`PASS`, `FAIL`, `ERROR`, `UNSUPPORTED`, `INCOMPLETE`).

### `OverallOutcome` Precedence Rules

1. Any `ERROR` status (assertion error or recalculation failure) → `ERROR`.
2. Any `FAIL` status (failed assertion) → `FAIL`.
3. Any `UNSUPPORTED` status → `UNSUPPORTED`.
4. Any `INCOMPLETE` status → `INCOMPLETE`.
5. All assertions `PASS` (and total > 0) → `PASS`.

---

## Code Example

```python
from finance_model_testbench import (
    ScenarioRunner,
    ReportGenerator,
    TestDefinition,
    AssertionType,
    CellReference,
    absolute_tolerance,
)

runner = ScenarioRunner()
test_def = TestDefinition(
    test_id="TD_BS_BALANCE",
    description="Total Assets == Total Liabilities + Equity",
    assertion_type=AssertionType.EQUALITY,
    operands=[
        CellReference("Balance Sheet", "C5"),
        CellReference("Balance Sheet", "C12"),
    ],
    tolerance=absolute_tolerance(0.01),
)

exec_res = runner.run("path/to/model.xlsx", [test_def])

generator = ReportGenerator()
report = generator.generate_report(exec_res, [test_def])

# Export JSON
json_output = report.to_json()

# Export Markdown
markdown_output = report.to_markdown()

print(f"Report Outcome: {report.summary.overall_outcome.value}")
```

---

## Security & Privacy Controls

* **Local-First Processing**: No network calls, telemetry, or external reporting services.
* **Path Sanitization**: Reports contain only file basenames by default to avoid leaking local user directory structures.
* **Markdown Injection Safeguards**: String fields are sanitized to escape backticks, pipes, and control characters.
* **Byte Immutability**: Source workbook files are never modified by report generation.

---

## Supported Files

```text
src/finance_model_testbench/report_models.py    — Report schema & serialization
src/finance_model_testbench/report_generator.py — Report assembly & outcome precedence
tests/test_reports.py                          — C6 test suite (11 tests)
docs/C6_EVIDENCE_LINKED_REPORTS.md              — C6 architecture documentation
```
