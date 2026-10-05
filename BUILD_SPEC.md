# BUILD_SPEC.md — Finance-Model-Testbench

---

# 1. PRODUCT IDENTITY

Product name:

**Finance-Model-Testbench**

Repository type:

**Open-source Python engineering project**

Operating philosophy:

**Local-first, deterministic-first, reproducible, security-conscious, minimal complexity.**

Primary purpose:

Build a narrowly scoped testbench for financial models that can verify explicit financial relationships and expected model behaviour under controlled conditions.

The project must focus on testing rather than generic spreadsheet auditing.

---

# 2. PROBLEM

Financial models can contain errors that are not necessarily obvious from visual inspection.

Examples include:

* broken financial relationships
* incorrect roll-forwards
* inconsistent statements
* incorrect formula logic
* assumptions that produce implausible model behaviour
* scenario changes that do not propagate as expected
* calculations that appear structurally valid but produce incorrect financial outcomes

Traditional spreadsheet auditing tools already address many structural and formula-level problems.

Therefore the project must NOT simply reproduce:

> "Find errors in Excel."

The intended problem is narrower:

> **Test whether a financial model satisfies explicitly defined financial assertions and behaves as expected when controlled assumptions change.**

The value proposition must therefore be based on:

* explicit financial assertions
* controlled scenarios
* deterministic execution
* reproducible results
* evidence-linked failures
* automated regression testing

---

# 3. DIFFERENTIATION REQUIREMENT

Generic spreadsheet auditing is an existing category.

The project must explicitly distinguish itself from:

* formula/error scanners
* workbook comparison tools
* generic spreadsheet auditors
* spreadsheet AI assistants
* general-purpose Excel automation tools

The core distinction to validate is:

**Model testing as a repeatable test suite rather than one-time spreadsheet inspection.**

The project should behave conceptually closer to software testing:

```text
financial model
      ↓
defined assertions
      ↓
controlled scenario
      ↓
recalculation
      ↓
assertions rerun
      ↓
structured evidence
      ↓
PASS / FAIL / ERROR / UNSUPPORTED
```

Do not claim that this differentiation is automatically unique.

The implementation must remain narrow enough that its measurable value can be evaluated.

---

# 4. TARGET USERS

Primary intended users:

* financial analysts
* FP&A analysts
* investment-banking analysts
* private-equity / transaction-model users
* finance students and practitioners
* developers building financial-model tooling

The project is an engineering tool, not a consumer finance application.

---

# 5. INITIAL MODEL SCOPE

The initial scope should focus on structured financial models where deterministic relationships can be tested.

Priority examples:

1. Three-statement models.
2. Operating models.
3. LBO / transaction models where technically feasible within the approved implementation scope.

Do not attempt to support every Excel feature.

Do not promise universal workbook compatibility.

Unsupported functionality must be detected and reported safely.

---

# 6. CORE PRODUCT CONCEPT

The system should allow a model to be tested against a set of explicit assertions.

Conceptually:

```text
Model
+
Test definitions
+
Scenario inputs
=
Test execution
+
Evidence
```

A test should be able to define:

* what is being tested
* which model elements are relevant
* expected financial relationship
* acceptable tolerance where numerical comparison is required
* optional scenario input changes
* expected outcome

The exact API and implementation structure must be designed later according to this specification and validated during implementation.

Do not overdesign the API before necessary requirements are established.

---

# 7. FINANCIAL ASSERTION CATEGORIES

The initial test engine should support the financial relationships approved during implementation planning.

Candidate categories include:

### Statement integrity

Examples:

* assets = liabilities + equity
* cash-flow relationships
* statement linkage consistency

### Roll-forward integrity

Examples:

```text
Ending Balance =
Beginning Balance
+ Additions
- Reductions
```

Potential applications:

* debt
* cash
* retained earnings
* fixed assets
* working capital

### Cross-statement consistency

Examples:

* net income flowing into retained earnings
* depreciation affecting both income statement and cash flow
* debt changes affecting cash flow and balance sheet
* working-capital movements affecting cash flow

### Scenario behaviour

Examples:

* revenue assumption increases
* operating margin changes
* capex changes
* debt assumptions change
* interest assumptions change

The model should then be tested against explicitly defined expected behaviour.

IMPORTANT:

These are candidate categories, not permission to implement every possible financial rule.

The final assertion catalogue must remain small and testable.

Any rule requiring professional accounting judgement must be explicitly specified before implementation.

---

# 8. NUMERICAL TOLERANCE

Financial calculations frequently involve floating-point arithmetic and rounding.

The system must support an explicit tolerance mechanism where appropriate.

A passing comparison must never depend on arbitrary hard-coded tolerances hidden inside implementation code.

Tolerance should be:

* explicit
* documented
* deterministic
* testable

The specification must distinguish:

* exact equality
* absolute tolerance
* relative tolerance

Do not invent a universal tolerance value without justification.

---

# 9. SCENARIO TESTING

Scenario testing is a central component of the project.

A scenario should represent controlled changes to selected model assumptions.

Example conceptual workflow:

```text
BASE CASE
    ↓
record baseline outputs
    ↓
change approved input
    ↓
recalculate model
    ↓
evaluate assertions
    ↓
compare observed behaviour
```

The system must preserve the distinction between:

* baseline state
* modified scenario state
* expected result
* observed result

The original source workbook must never be silently destroyed.

Scenario execution must operate on a safe copy or equivalent isolated representation.

---

# 10. RECALCULATION

Workbook libraries that only read/write formulas are not sufficient for numerical recalculation.

The architecture must therefore explicitly separate:

1. workbook inspection
2. formula representation
3. spreadsheet calculation
4. assertion evaluation

If a spreadsheet calculation engine is required, the chosen engine must be:

* locally executable where possible
* reproducible
* automatable
* compatible with the supported workbook scope
* safely isolated

Do not assume that a Python workbook library calculates formulas.

Do not silently treat stale cached formula values as freshly calculated values.

If recalculation cannot be performed reliably:

**return an explicit ERROR or UNSUPPORTED state according to the final status semantics.**

---

# 11. EVIDENCE

Every failed or otherwise non-passing assertion should provide useful evidence.

Where technically available, evidence should include:

* test identifier
* assertion type
* workbook/sheet
* relevant cell or range
* expected condition
* observed value
* expected value or relationship
* tolerance
* scenario name
* execution status
* concise failure explanation

Evidence must be machine-readable.

A human-readable Markdown report should also be possible where required by the implementation phase.

Do not expose unnecessary confidential workbook contents.

---

# 12. TEST RESULT MODEL

The implementation should distinguish between different execution outcomes.

The initial conceptual statuses are:

```text
PASS
FAIL
ERROR
UNSUPPORTED
INCOMPLETE
```

Definitions must be precise.

### PASS

The assertion was evaluated and its condition was satisfied.

### FAIL

The assertion was evaluated and its condition was not satisfied.

### ERROR

The test could not be reliably evaluated because execution encountered an error.

### UNSUPPORTED

The workbook/model feature required for the test is outside the supported implementation scope.

### INCOMPLETE

The test execution was interrupted or lacked required information.

Do not convert ERROR, UNSUPPORTED, or INCOMPLETE into PASS.

Do not hide failures behind generic exceptions.

---

# 13. INPUT VALIDATION

The system must validate incoming workbooks before attempting complex operations.

Validation should consider:

* file type
* workbook readability
* required sheets
* required cells/ranges
* formula availability
* missing inputs
* malformed structures
* unsupported workbook features

Invalid input should produce a controlled result rather than an uncontrolled crash.

---

# 14. SECURITY REQUIREMENTS

Financial workbooks should be treated as untrusted input.

The system must not:

* execute arbitrary workbook macros
* execute arbitrary code embedded in workbook content
* upload workbook data to external services by default
* expose sensitive workbook data through logs
* overwrite the original workbook
* store secrets inside repository files

The project should be local-first.

External network communication is prohibited unless explicitly justified and approved.

Security controls must be tested during C7.

---

# 15. PRIVACY

The project must support safe use with potentially confidential financial models.

Design principles:

* local processing by default
* minimal data retention
* no telemetry by default
* no external model/API dependency by default
* synthetic data for public examples
* no credentials in fixtures
* no real confidential company workbooks in the repository

---

# 16. OPEN-SOURCE REQUIREMENTS

The project is intended to be published publicly on GitHub.

The final repository must contain:

* clear installation instructions
* usage examples
* architecture overview
* supported/unsupported functionality
* testing instructions
* limitations
* licence
* contribution information where appropriate

Do not claim enterprise readiness without evidence.

Do not claim universal Excel compatibility.

---

# 17. INITIAL TECHNICAL DIRECTION

Preferred implementation language:

**Python**

Likely technical components may include:

* workbook parsing/manipulation library
* local spreadsheet calculation engine where necessary
* deterministic assertion engine
* structured result model
* JSON reporting
* Markdown reporting
* pytest-based testing

These are implementation directions, not permission to add unnecessary dependencies.

Dependency choices must be justified and remain consistent with the local-first and minimal-complexity principles.

---

# 18. ARCHITECTURAL PRINCIPLES

The architecture should separate:

```text
Input / Workbook Layer
        ↓
Inspection Layer
        ↓
Calculation / Scenario Layer
        ↓
Assertion Engine
        ↓
Evidence / Reporting Layer
```

Security and validation should apply across the pipeline.

Keep interfaces small.

Prefer composable modules over a monolithic implementation.

Avoid unnecessary frameworks.

Avoid unnecessary abstraction layers.

---

# 19. AI REQUIREMENT

The project does NOT require an LLM.

The core test engine must function deterministically without an LLM.

AI may only be introduced later if a clearly defined use case demonstrates measurable benefit.

Potential future examples could include:

* natural-language explanation of failures
* mapping user-described financial checks to formal assertions
* assistance with test creation

These are explicitly OUT OF INITIAL SCOPE unless separately approved.

Do not add AI merely for marketing.

---

# 20. BENCHMARK REQUIREMENTS

The project must eventually demonstrate measurable behaviour.

The benchmark should include:

* valid models
* intentionally defective models
* different defect categories
* expected detection results
* unsupported cases
* false-positive evaluation where applicable

Metrics must be calculated from a clearly defined test population.

Do not fabricate benchmark results.

Do not use synthetic benchmark performance as evidence of real-world effectiveness without clearly labelling it.

---

# 21. TEST FIXTURE REQUIREMENTS

Public fixtures must be synthetic.

Fixtures should include:

### Valid models

Models where approved assertions should pass.

### Defective models

Controlled defects designed to test specific failure modes.

Potential defect classes:

* incorrect formula
* broken link
* incorrect roll-forward
* statement imbalance
* incorrect scenario propagation
* intentionally unsupported feature

Every defect fixture must have a known expected result.

---

# 22. IMPLEMENTATION PHASES

The implementation sequence is frozen:

```text
C1 — Workspace & Configuration
C2 — Financial Test Fixtures
C3 — Workbook Inspection
C4 — Deterministic Test Engine
C5 — Scenario Execution
C6 — Evidence-Linked Reports
C7 — Security & Error Handling
C8 — Benchmark & Regression Tests
C9 — Documentation & Release Preparation
C10 — Final Audit & GitHub Publication
```

No implementation begins during specification authoring.

---

# 23. PHASE ACCEPTANCE LOGIC

Every phase must have explicit acceptance criteria.

A phase is complete only when:

* required implementation exists
* targeted tests pass
* relevant negative tests pass
* specification requirements are satisfied
* diff has been inspected
* project state has been updated
* no unresolved blocker remains

The coding agent must not mark a phase complete merely because the code runs.

---

# 24. OUT-OF-SCOPE FEATURES

Unless explicitly added through a later approved specification change, the following are outside the initial product:

* cloud SaaS
* multi-user collaboration
* user accounts
* authentication
* payments
* dashboards
* mobile applications
* browser extensions
* autonomous financial advice
* investment recommendations
* trading functionality
* portfolio management
* automated model repair
* LLM dependency
* external financial-data dependency
* proprietary enterprise integrations
* automatic workbook publishing
* unrestricted Excel feature support

---

# 25. SUCCESS CRITERIA

The project should ultimately demonstrate that it can:

1. Load supported financial workbooks safely.
2. Validate their structure.
3. Execute approved deterministic financial assertions.
4. Run controlled scenarios where supported.
5. Recalculate reliably where required.
6. Detect deliberately introduced model defects.
7. Produce evidence explaining test outcomes.
8. Handle unsupported or malformed inputs safely.
9. Reproduce results.
10. Provide measurable benchmark evidence.

The project succeeds technically only if these behaviours are demonstrated through tests and evidence.

---

# 26. LIMITATIONS

The project must openly acknowledge that:

* Excel is extremely feature-rich.
* Not every workbook feature will be supported.
* Some financial-model correctness requires professional judgement.
* Formula-level correctness does not guarantee business correctness.
* Synthetic tests cannot fully represent real-world financial models.
* Recalculation engines may differ from Microsoft Excel.
* A passing test suite does not prove that a model is economically or commercially correct.

These limitations must remain visible in the final documentation.

---

# 27. ENGINEERING PRIORITY ORDER

When making implementation decisions, use this priority:

```text
1. Correctness
2. Financial validity
3. Security
4. Reproducibility
5. Testability
6. Simplicity
7. Maintainability
8. Performance
9. Convenience
10. Visual polish
```

Do not sacrifice correctness for speed of implementation.

Do not sacrifice security for convenience.

Do not sacrifice reproducibility for feature breadth.

---

# 28. CHANGE CONTROL

This specification is the approved implementation boundary.

If a coding agent discovers that implementation requires:

* a new major feature
* a new external dependency
* a new architecture
* a new financial rule
* a new data source
* a change to acceptance criteria
* a change to phase order

it must stop and request approval.

It must NOT silently modify this specification to justify its implementation.

---

# 29. CURRENT STATUS

At the time of authoring this specification:

* repository structure exists
* `AGENTS.md` exists
* no source code exists
* no tests exist
* no dependencies are installed
* no implementation phase has started
* C1 is not authorised yet

The next operational document to prepare is `PROJECT_STATE.md`.

---

# 30. SPECIFICATION AUTHORING COMPLETION

After writing this specification:

1. Save it as exactly:

```text
BUILD_SPEC.md
```

2. Do not modify any other project file.
3. Verify that the file exists.
4. Verify that no source code was created.
5. Verify that no dependencies were installed.
6. Verify that no implementation phase began.
7. Stop.
