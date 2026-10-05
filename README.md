# Finance-Model-Testbench

**A local-first, deterministic testbench for testing financial-model behaviour through explicit assertions and controlled scenarios.**

Finance-Model-Testbench is a local-first Python testbench for structured financial models. It evaluates explicit financial assertions, runs controlled assumption scenarios, and produces reproducible evidence. It is deterministic-first and does not require an LLM.

## The Problem

Financial models can contain errors that are not obvious from visual inspection alone.

Examples include:

* Broken financial relationships that appear structurally intact
* Incorrect roll-forwards for debt, retained earnings, fixed assets, or working capital
* Inconsistent linkages across the income statement, balance sheet, and cash-flow statement
* Formula logic that produces plausible-looking but incorrect outputs
* Assumption changes that do not propagate correctly through the model
* Calculations that pass manual review but fail under controlled test conditions

Generic spreadsheet auditing is an established category. Finance-Model-Testbench targets a narrower problem:

> **Test whether a financial model satisfies explicitly defined financial assertions and behaves as expected when controlled assumptions change.**

The project treats financial-model validation as a repeatable test suite rather than a one-time structural inspection.

## Core Idea

```text
Financial Model
      ↓
Defined Assertions
      ↓
Controlled Scenario
      ↓
Recalculation
      ↓
Assertions Re-run
      ↓
Evidence
      ↓
Test Result
```

Each test defines what is being evaluated, which model elements are involved, the expected financial relationship, the acceptable tolerance, and the resulting status.

The goal is not to replace professional financial-model review, but to make specific model relationships testable, reproducible, and evidence-based.

## Differentiation

Finance-Model-Testbench deliberately does **not** attempt to become another generic spreadsheet-auditing platform.

Its narrower focus is:

> **Explicit financial assertions + controlled scenarios + reproducible evidence.**

This is analogous to applying software-testing principles to financial models: define expected relationships, execute tests, isolate controlled changes, and retain evidence of the result.

The project does not claim that this approach solves all financial-model validation problems. Its value is evaluated through implementation, testing, and benchmarking.

## Intended Users

* Financial analysts
* FP&A analysts
* Investment-banking analysts
* Private-equity and transaction-model users
* Finance students and practitioners
* Developers building financial-model tooling

This is an engineering tool, not a consumer finance application.

## Current Capabilities

The current implementation provides:

* Read-only `.xlsx` workbook inspection
* Formula and cached-value provenance during inspection
* Explicit `EQUALITY`, `DIFFERENCE`, and `SUM_EQUALITY` assertions
* `EXACT`, `ABSOLUTE`, and `RELATIVE` tolerance handling
* Controlled scenario inputs
* Isolated local recalculation through `xlcalculator`
* Source-workbook immutability verification
* Structured statuses:

  * `PASS`
  * `FAIL`
  * `ERROR`
  * `UNSUPPORTED`
  * `INCOMPLETE`
* Deterministic JSON evidence reports
* Human-readable Markdown reports
* Deterministic benchmark and regression testing
* Security-focused input validation and error handling

## Supported Financial Test Types

### Statement Integrity

Example:

```text
Total Assets = Total Liabilities + Equity
```

### Roll-Forward Integrity

Example:

```text
Ending Retained Earnings
    =
Beginning Retained Earnings
    + Net Income
    - Dividends
```

The same principle can be applied to other model balances such as debt, fixed assets, cash, and working capital.

### Cross-Statement Consistency

Examples include:

```text
Net Income → Retained Earnings
Depreciation → Income Statement + Cash Flow
Debt Movement → Balance Sheet + Cash Flow
```

### Scenario Behaviour

A controlled input change can be applied, the model recalculated, and the assertions rerun to test whether the expected relationships continue to hold.

## Assertion Engine

The current assertion engine supports three assertion types.

### Equality

```text
A == B
```

### Difference

```text
A - B == Expected
```

### Sum Equality

```text
A + B + C == Expected
```

Tolerance modes:

```text
EXACT
ABSOLUTE
RELATIVE
```

The assertion engine is deterministic: the same inputs and definitions produce the same result.

## Controlled Scenario Execution

Scenario execution follows:

```text
Baseline
   ↓
Change Defined Input
   ↓
Recalculate in Isolated Workspace
   ↓
Rerun Assertions
   ↓
Produce Evidence
```

The original workbook is not overwritten during scenario execution.

Scenario execution therefore allows controlled behavioural testing without modifying the source model.

## Evidence and Reporting

Test results retain the information required to understand an outcome, including:

* Test ID
* Assertion type
* Workbook reference
* Worksheet and cell reference
* Expected condition/value
* Observed value
* Tolerance
* Scenario information
* Status
* Explanation

Reports are available in:

```text
JSON
Markdown
```

Report generation is deterministic and avoids exposing unnecessary absolute filesystem paths.

## Status Semantics

```text
PASS
```

The evaluated assertion satisfied its defined condition.

```text
FAIL
```

The assertion was evaluated successfully but its condition was not satisfied.

```text
UNSUPPORTED
```

The requested operation or workbook feature is outside the supported implementation scope.

```text
INCOMPLETE
```

The test could not be fully evaluated because required calculation or evaluation information was unavailable.

```text
ERROR
```

An execution or processing error prevented reliable evaluation.

These statuses are intentionally distinct. Unsupported or failed execution must not silently become `PASS`.

## Architecture

```text
Input Workbook
      │
      ▼
Workbook Inspection
      │
      ▼
Calculation / Scenario Execution
      │
      ▼
Assertion Engine
      │
      ▼
Evidence & Reporting
```

The implementation separates:

* Workbook inspection
* Recalculation
* Scenario execution
* Assertion evaluation
* Evidence generation
* Reporting

`openpyxl` is used for workbook structure and data access. It does not calculate Excel formulas, so recalculation is handled separately through the local `xlcalculator` layer.

## Installation

Python 3.10 or newer is required.

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

Install the package:

```powershell
python -m pip install .
```

For development and testing:

```powershell
python -m pip install ".[dev]"
```

## Quick Start

A basic workbook inspection can be performed through the public API:

```python
from finance_model_testbench import WorkbookInspector

result = WorkbookInspector().inspect("model.xlsx")

print(result)
```

For assertion and scenario workflows, see the implementation and documentation under `docs/`.

## Benchmark

The project contains a deterministic benchmark built from synthetic financial-model fixtures.

Current benchmark composition:

| Case                                  | Type      | Expected |
| ------------------------------------- | --------- | -------- |
| Valid three-statement model           | Baseline  | PASS     |
| Balance-sheet imbalance               | Defective | FAIL     |
| Retained-earnings roll-forward defect | Defective | FAIL     |
| Cash-flow linkage defect              | Defective | FAIL     |
| Controlled revenue-growth scenario    | Scenario  | PASS     |

Current verified benchmark:

```text
Cases:                    5
Correct classifications: 5/5
Known defect detections:  3
False positives:          0
Unsupported:              0
Incomplete:               0
Errors:                   0
```

The benchmark is intentionally small and synthetic.

**The 5/5 result is not a claim of 100% real-world financial-model accuracy or defect-detection coverage.**

It demonstrates deterministic correctness against the project's current known benchmark cases.

Run the benchmark using the documented project workflow.

See:

`docs/C8_BENCHMARK_AND_REGRESSION.md`

## Security and Privacy

Finance-Model-Testbench is designed around local-first processing.

The project does not require:

* Cloud processing
* User accounts
* External workbook uploads
* Telemetry
* Trading integrations
* Financial-data subscriptions
* LLM access

Security-oriented controls include:

* Read-only source workbook handling
* SHA-256 source integrity verification
* Isolated scenario workspaces
* Input-path validation
* Sanitized error reporting
* Markdown output escaping
* Bounded error-log exposure
* No macro execution
* No arbitrary workbook code execution
* Synthetic public fixtures
* No credentials or private financial data in the repository

Users should still treat financial workbooks as sensitive information and operate the tool within an appropriately secured environment.

## Limitations

Finance-Model-Testbench does **not** attempt to provide complete Excel compatibility.

Important limitations include:

* Excel has a very large feature surface.
* `openpyxl` does not calculate formulas.
* `xlcalculator` does not reproduce every Excel calculation feature or semantic exactly.
* Some workbook features may be unsupported.
* Formula correctness does not guarantee business correctness.
* Financial-model correctness may require professional judgement.
* The benchmark is small and synthetic.
* Local calculation-engine behaviour may differ from Microsoft Excel in edge cases.

Unsupported or incomplete situations are reported rather than silently ignored.

A passing test suite does not prove that a financial model is economically, commercially, or strategically sound.

## Deterministic-First

The core test engine does not require AI.

This is deliberate.

The project follows the principle:

> **Deterministic before intelligent.**

Financial assertions should be explicit, mathematically or structurally defined, reproducible, and testable.

AI is not introduced merely for marketing purposes.

Any future AI-assisted capability would require a clearly defined use case and measurable benefit without weakening deterministic validation.

## Project Structure

```text
Finance-Model-Testbench/
│
├── src/
│   └── finance_model_testbench/
│       ├── __init__.py
│       ├── assertion_engine.py
│       ├── assertion_models.py
│       ├── benchmark.py
│       ├── config.py
│       ├── exceptions.py
│       ├── generate_fixtures.py
│       ├── inspector.py
│       ├── models.py
│       ├── recalculator.py
│       ├── report_generator.py
│       ├── report_models.py
│       ├── scenario_models.py
│       └── scenario_runner.py
│
├── tests/
│   ├── test_assertion_engine.py
│   ├── test_benchmark.py
│   ├── test_fixtures.py
│   ├── test_foundation.py
│   ├── test_inspector.py
│   ├── test_reports.py
│   ├── test_scenario_runner.py
│   └── test_security.py
│
├── examples/
│   └── fixtures/
│       ├── defective/
│       ├── manifests/
│       ├── scenarios/
│       └── valid/
│
├── docs/
├── research/
├── AGENTS.md
├── BUILD_SPEC.md
├── CONTRIBUTING.md
├── LICENSE
├── PROJECT_STATE.md
├── pyproject.toml
└── README.md
```

## Development

Run the complete automated test suite:

```powershell
python -m pytest -ra -v
```

The current verified suite contains:

```text
160 passed
0 failed
0 errors
```

The exact test count may change as the project evolves.

## Development Roadmap

```text
C1   Workspace & Configuration          COMPLETE
C2   Financial Test Fixtures            COMPLETE
C3   Workbook Inspection                COMPLETE
C4   Deterministic Test Engine          COMPLETE
C5   Calculation & Scenario Execution   COMPLETE
C6   Evidence-Linked Reports            COMPLETE
C7   Security & Error Handling          COMPLETE
C8   Benchmark & Regression Tests       COMPLETE
C9   Documentation & Release Prep       COMPLETE
C10  Final Technical Audit              COMPLETE
```

The implementation has passed the project's final technical audit and release-readiness checks.

## Design Principles

### 1. Deterministic before intelligent

Core financial validation should produce reproducible results without requiring an LLM.

### 2. Explicit financial logic

Tests should express what must be true rather than relying on opaque heuristics.

### 3. Evidence over assertions alone

A failed test should provide enough context to understand what failed and where.

### 4. Source immutability

Testing should not silently modify the original financial model.

### 5. Local-first processing

Financial workbooks should not need to leave the user's environment.

### 6. Fail safely

Unsupported or ambiguous situations should be reported rather than silently treated as valid.

### 7. Small, testable scope

The project deliberately avoids becoming a generic Excel platform.

## Scope Boundaries

Finance-Model-Testbench is **not**:

* A general-purpose spreadsheet auditor
* An Excel replacement
* An automated model-repair system
* A financial-advice system
* A trading system
* A portfolio-management platform
* A cloud SaaS platform
* A mobile application
* A browser extension
* An unrestricted Excel execution environment
* A mandatory LLM-based system

The project focuses on:

> **Explicit financial assertions, controlled scenarios, and reproducible evidence.**

## Contributing

Contributions are welcome when they preserve the project's deterministic, security-conscious architecture and documented scope.

Before contributing:

1. Review `AGENTS.md`.
2. Review `BUILD_SPEC.md`.
3. Review `PROJECT_STATE.md`.
4. Make focused changes.
5. Add or update regression tests.
6. Run the complete test suite.
7. Run the benchmark.
8. Inspect the resulting changes.

Avoid unrelated features, unnecessary dependencies, and scope expansion.

See `CONTRIBUTING.md` for contribution guidance.

## Project Status

**Version:** `0.1.0`

**Implementation:** C1–C10 complete

**Release readiness:** Technical audit passed

**Benchmark:** 5/5 synthetic cases correctly classified

**License:** MIT

The project is early-stage software and should be treated as an engineering validation tool rather than a replacement for professional financial-model review.

## License

This project is released under the MIT License.

See `LICENSE` for the full license text.
