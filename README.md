# Finance-Model-Testbench

**A local-first, deterministic testbench for testing financial-model behaviour through explicit assertions and controlled scenarios.**

> **Status: Pre-implementation.** This repository is in the specification and planning stage. No functionality currently exists. Implementation has not started.

---

## The Problem

Financial models can contain errors that are not obvious from visual inspection alone.

Examples include:

- Broken financial relationships that appear structurally intact
- Incorrect roll-forwards for debt, retained earnings, fixed assets, or working capital
- Inconsistent statement linkages across income statement, balance sheet, and cash flow
- Formula logic errors that produce plausible-looking but incorrect outputs
- Assumption changes that do not propagate correctly through the model
- Calculations that pass manual review but fail under controlled test conditions

Traditional spreadsheet auditing tools address many structural and formula-level problems. Finance-Model-Testbench targets a narrower problem:

> **Test whether a financial model satisfies explicitly defined financial assertions and behaves as expected when controlled assumptions change.**

---

## Core Idea

The project approaches financial-model validation as a repeatable test suite rather than a one-time structural inspection.

```
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
Test Result: PASS / FAIL / ERROR / UNSUPPORTED
```

Each test should define what is being evaluated, which model elements are involved, the expected financial relationship, the acceptable tolerance, and the expected outcome. Results are evidence-linked and structured for both machine consumption and human review.

---

## Differentiation

Generic spreadsheet auditing is an established product category. Tools such as Spreadsheet Auditor and Macabacus Model Check already provide formula-error scanning, structural validation, broken-link detection, and similar checks.

Finance-Model-Testbench does not aim to reproduce those capabilities.

The differentiation hypothesis is:

> Treat financial-model validation as a repeatable test suite with explicit financial assertions and controlled scenarios — analogous to software unit testing — rather than as a one-time spreadsheet inspection.

Whether this approach provides meaningful practical value beyond existing tools will be evaluated through implementation, testing, and benchmarking. This hypothesis is not assumed to be proven.

---

## Intended Users

- Financial analysts
- FP&A analysts
- Investment-banking analysts
- Private-equity and transaction-model users
- Finance students and practitioners
- Developers building financial-model tooling

This project is an engineering tool. It is not a consumer finance application.

---

## Initial Model Scope

The initial implementation scope targets structured financial models where deterministic relationships can be explicitly tested:

1. Three-statement financial models
2. Operating models
3. Selected LBO / transaction-model scenarios where technically feasible

Universal Excel compatibility is not a goal. Unsupported workbook features will be detected and reported rather than silently ignored.

---

## Planned Capabilities

The following capabilities are **planned and not yet implemented**:

- Safe workbook loading and structural validation
- Deterministic financial assertions
- Numerical tolerance handling (exact, absolute, relative)
- Controlled scenario execution with assumption changes
- Local recalculation where supported by the chosen engine
- Evidence-linked test results with workbook references
- JSON-structured output
- Markdown reporting
- Safe handling of malformed, unsupported, or untrusted workbooks
- Regression and benchmark testing against synthetic fixture sets

The final assertion catalogue and implementation details are controlled by `BUILD_SPEC.md`.

---

## Example Financial Assertions (Conceptual)

The following are illustrative examples only. The authoritative assertion catalogue will be defined and implemented incrementally according to the approved specification.

**Statement integrity:**

```
Assets = Liabilities + Equity
```

**Roll-forward integrity:**

```
Ending Balance =
    Beginning Balance
    + Additions
    − Reductions
```

Applications may include debt, cash, retained earnings, fixed assets, and working capital.

**Cross-statement consistency:**

- Net income flowing correctly into retained earnings
- Depreciation consistent across income statement and cash-flow statement
- Debt movements consistent across balance sheet and cash-flow statement

**Scenario behaviour:**

- A revenue assumption increase should produce an expected directional change in operating income
- A capex change should propagate consistently through fixed assets and cash flow

---

## Deterministic-First

The core test engine is designed to be deterministic and reproducible without requiring a large language model.

- Financial assertions are expressed mathematically or structurally where possible
- Results must be reproducible from the same inputs
- AI is not being introduced for marketing purposes
- Any future AI-assisted capability would require a clearly defined and measurable benefit

---

## Local-First and Security

The project is designed around local processing:

- Workbooks are treated as untrusted input
- The original source workbook is never overwritten
- Workbook macros are not executed
- External links are not followed automatically
- Workbook data is not transmitted to external services by default
- No telemetry by default
- Public fixtures use synthetic data only

Security controls will be implemented and tested during the C7 phase.

---

## Current Project Status

```
Status:             Pre-implementation
Current phase:      None
C1 authorised:      No
Implementation:     Not started
```

The repository currently contains the project specification, execution rules, and operational ledger. No source code, tests, or fixtures exist. No dependencies have been installed.

---

## Development Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| C1 | Workspace & Configuration | Not started |
| C2 | Financial Test Fixtures | Not started |
| C3 | Workbook Inspection | Not started |
| C4 | Deterministic Test Engine | Not started |
| C5 | Scenario Execution | Not started |
| C6 | Evidence-Linked Reports | Not started |
| C7 | Security & Error Handling | Not started |
| C8 | Benchmark & Regression Tests | Not started |
| C9 | Documentation & Release Preparation | Not started |
| C10 | Final Audit & GitHub Publication | Not started |

Each phase must be explicitly authorised before it begins. Phases are completed sequentially.

---

## Repository Structure

```
Finance-Model-Testbench/
├── AGENTS.md              — Permanent coding-agent execution rules
├── BUILD_SPEC.md          — Approved product and technical specification
├── PROJECT_STATE.md       — Operational project ledger and phase tracking
├── README.md              — This file
├── research/
│   ├── RESEARCH_DOSSIER.md   — Research archive
│   └── SOURCES.md            — Research sources
├── src/                   — Future implementation (currently empty)
├── tests/                 — Future test suite (currently empty)
└── examples/              — Future examples (currently empty)
```

---

## Out of Scope

The following are explicitly excluded from the initial project:

- Cloud SaaS or hosted deployment
- Multi-user collaboration
- User accounts or authentication
- Payments
- Dashboards or GUI applications
- Mobile applications or browser extensions
- Autonomous financial advice or investment recommendations
- Trading or portfolio management functionality
- Automated model repair
- Mandatory LLM usage
- Proprietary enterprise integrations
- Unrestricted Excel feature support

---

## Known Limitations

- Excel has a very large feature surface. Not every workbook feature will be supported.
- Some financial-model correctness requires professional accounting judgement that cannot be captured in deterministic assertions.
- Formula-level correctness does not guarantee business or commercial correctness.
- Synthetic benchmark results cannot fully represent real-world financial model populations.
- Local spreadsheet calculation engines may produce results that differ from Microsoft Excel in edge cases.
- A passing test suite does not prove that a model is economically sound.

---

## Technology

```
Language:      Python
Architecture:  Local-first
Testing:       pytest-oriented
Core approach: Deterministic assertions
```

Specific dependencies will be selected during the C1 phase according to the approved specification principles: minimal, justified, locally executable, and reproducible.

Installation instructions and usage documentation will be added during the C9 release-preparation phase.

---

## Contributing

Development documentation and contribution guidance will be expanded during the release-preparation phase (C9).

---

## Licence

> Licence: To be finalised before public release.

The licence will be explicitly selected and added during the approved release process (C10).
# Finance-Model-Testbench

Finance-Model-Testbench is a local-first Python testbench for structured financial models. It evaluates explicit financial assertions, runs controlled assumption scenarios, and produces reproducible evidence. It is deterministic-first and does not require an LLM.

## Problem and approach

Financial models can contain broken relationships, incorrect roll-forwards, inconsistent statement links, and unexpected scenario behaviour. This project treats those relationships as repeatable tests rather than attempting to be a generic Excel auditor.

```text
Financial model → inspection → recalculation/scenario → explicit assertions → evidence/report
```

Generic spreadsheet auditing is an established category. The narrower focus here is explicit financial assertions, controlled scenarios, and reproducible evidence.

## Current capabilities

- Read-only inspection of `.xlsx` workbooks with formula and cached-value provenance.
- Explicit `EQUALITY`, `DIFFERENCE`, and `SUM_EQUALITY` assertions.
- `EXACT`, `ABSOLUTE`, and `RELATIVE` tolerances.
- Controlled scenario inputs with isolated recalculation through `xlcalculator`.
- Structured statuses: `PASS`, `FAIL`, `ERROR`, `UNSUPPORTED`, and `INCOMPLETE`.
- Deterministic JSON and Markdown evidence reports.
- A five-case synthetic benchmark covering a valid model, three known defects, and a scenario.

The supported scope is intentionally limited. This is not unrestricted Excel compatibility or a generic spreadsheet-auditing product.

## Installation

Python 3.10 or newer is declared by `pyproject.toml`; Python 3.12.10 was used for the current verification.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Quick start

The public API is available from `finance_model_testbench`:

```python
from finance_model_testbench import (
    AssertionType, CellReference, ScenarioRunner, TestDefinition,
    absolute_tolerance,
)

test = TestDefinition(
    test_id="TD_BS_BALANCE",
    description="Total Assets equals Total Liabilities and Equity",
    assertion_type=AssertionType.EQUALITY,
    operands=[
        CellReference("Balance Sheet", "C5"),
        CellReference("Balance Sheet", "C12"),
    ],
    tolerance=absolute_tolerance(0.01),
)

result = ScenarioRunner().run(
    "examples/fixtures/valid/valid_three_statement.xlsx",
    [test],
)
print(result.assertion_results[0].status.value)
```

`ScenarioRunner` recalculates an isolated copy and verifies that the source workbook is unchanged. For a controlled input, pass a `ScenarioDefinition` containing `ScenarioInput` values.

## Reports and statuses

`ReportGenerator.generate_report(result, definitions)` returns a `TestbenchReport`; use `.to_json()` or `.to_markdown()` for output. Reports preserve assertion IDs, statuses, expected and observed values, tolerances, cell references, scenario inputs, and source identity without exposing absolute paths.

`FAIL` means an evaluated financial assertion did not hold. The benchmark can still succeed when a known defective fixture produces the expected `FAIL`: benchmark correctness compares `expected_status` with `actual_status`. `ERROR`, `UNSUPPORTED`, and `INCOMPLETE` are not silently converted to passes.

## Architecture

```text
Input workbook → WorkbookInspector → WorkbookRecalculator/ScenarioRunner
               → AssertionEngine → ReportGenerator
```

Inspection, recalculation, assertion evaluation, and reporting are separate layers. `openpyxl` reads and writes workbook structures but does not calculate Excel formulas, so recalculation is handled separately by the local `xlcalculator` layer.

## Benchmark

Run the current benchmark through its public Python API:

```powershell
python -c "from pathlib import Path; from finance_model_testbench import BenchmarkRunner; import json; print(json.dumps(BenchmarkRunner(Path.cwd()).run(), indent=2, sort_keys=True))"
```

The synthetic C8 benchmark contains 5 cases: 2 expected PASS cases (valid baseline and scenario) and 3 expected FAIL cases (statement imbalance, retained-earnings roll-forward, and cash-flow linkage). Current verification classified all 5 cases correctly, with 3 known defect detections and 0 valid-model false positives. This small synthetic corpus demonstrates tested-fixture correctness; it does not establish a real-world detection rate.

See [C8 benchmark and regression documentation](docs/C8_BENCHMARK_AND_REGRESSION.md).

## Repository structure

```text
src/       package implementation
tests/     C1–C8 automated tests
examples/  synthetic workbooks, taxonomy, and ground truth
docs/      phase and usage documentation
research/  background research archive
```

## Security, privacy, and limitations

Execution is local-first: there is no default workbook upload, telemetry, network requirement, or LLM dependency. The system does not execute macros or arbitrary workbook code, does not overwrite source fixtures, hashes source files for immutability checks, sanitizes report paths, and handles malformed inputs through explicit errors.

Excel has a large feature surface and not every workbook construct is supported. Calculation-engine semantics may differ from Microsoft Excel. Formula correctness does not guarantee business correctness, and professional financial judgement remains necessary. Unsupported or incomplete evaluations can occur. Public fixtures are synthetic and contain no confidential financial data.

The current deterministic core intentionally does not require AI. Any future AI layer would need a measurable use case and separate approval.

## Testing

```powershell
python -m pytest -ra -v
```

The current verified suite contains 160 passing tests across C1–C8; this count may change as the project evolves.

## Contributing

Create a virtual environment, install `.[dev]`, make focused changes, add regression tests, run the full suite and benchmark, and inspect the resulting files. Preserve the frozen phase order, explicit financial rules, local-first behavior, source immutability, and documented limitations. Avoid unrelated features and scope expansion.

See [fixture documentation](examples/fixtures/README.md), [defect taxonomy](examples/fixtures/DEFECT_TAXONOMY.md), and the phase documents in `docs/` for more detail.

## Project status

C1–C9 are complete. C10 — final audit and GitHub publication — has not started and requires explicit authorization. The project is pre-alpha and is not a substitute for professional financial-model review.

## License

MIT. See [LICENSE](LICENSE).
