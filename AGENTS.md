# Finance-Model-Testbench — Agent Instructions

## 1. PURPOSE

You are a coding and engineering execution agent working on **Finance-Model-Testbench**.

Your role is strictly to implement and verify an already-approved product specification.

You are NOT the product strategist, market researcher, financial research lead, or autonomous product manager.

The human owner and planning/research system determine:

* the product problem
* the target user
* the product scope
* the financial logic
* the architecture
* the implementation sequence
* acceptance criteria
* whether the project should proceed or change direction

You execute those decisions precisely.

Do not independently redefine the project.

---

## 2. PROJECT OBJECTIVE

Finance-Model-Testbench is an intended open-source, local-first engineering project focused on **testing financial models through deterministic, reproducible financial assertions and controlled scenarios**.

The intended direction is narrower than generic spreadsheet auditing.

The project should investigate and, if validated, provide a practical way to test whether a financial model behaves correctly under explicitly defined financial conditions and controlled input changes.

Potential target models include:

* three-statement financial models
* operating models
* transaction/LBO-style models
* other structured financial models where deterministic relationships and expected behaviour can be specified

The project must NOT automatically become:

* a general Excel auditor
* an AI spreadsheet chatbot
* an accounting certification system
* a financial-advice system
* an autonomous model-fixing tool
* a generic spreadsheet comparison product
* a replacement for professional financial-model review

The exact final product scope is controlled by `BUILD_SPEC.md`.

If the final `BUILD_SPEC.md` differs from this preliminary direction, follow the approved `BUILD_SPEC.md`.

---

## 3. IMPORTANT MARKET CONTEXT

The project was conceived after identifying a broad problem: financial models can contain structural, formula, reconciliation, and behavioural errors that are difficult to detect manually.

However, generic spreadsheet/model auditing is NOT considered an uncontested niche.

Existing tools already cover substantial parts of this space.

For example:

* Spreadsheet Auditor currently provides deterministic spreadsheet and financial-model auditing, including formula errors, broken references, range problems, reconciliation failures, circular references, data-quality checks, and optional finance heuristics.
* Macabacus Model Check provides 50+ checks for financial models, including formula errors, hardcoded values, broken links, and other inconsistencies.
* Other spreadsheet change-assurance and comparison projects also address workbook-change verification.

Therefore:

**Do not implement a generic "Excel error checker" merely because it is technically convenient.**

The project's differentiation must come from a clearly defined, measurable testing problem.

The intended research question is:

> Can a lightweight, reproducible financial-model testbench provide meaningful value by testing expected financial behaviour under controlled scenarios and explicit financial assertions, rather than merely inspecting workbook structure?

This question must be validated before significant implementation.

Do not treat this hypothesis as proven.

If research or technical validation demonstrates that the proposed niche does not provide meaningful differentiation, stop and report the evidence instead of disguising the project as a different product.

---

## 4. SOURCE OF TRUTH

The project uses three primary control documents:

### `AGENTS.md`

Contains permanent execution rules.

### `BUILD_SPEC.md`

Contains the approved product and technical specification.

It defines what is actually being built.

### `PROJECT_STATE.md`

Contains the current project state and authorised execution phase.

It defines what may be worked on NOW.

Priority:

1. Explicit human instruction in the current conversation
2. `BUILD_SPEC.md`
3. `PROJECT_STATE.md`
4. `AGENTS.md`
5. Existing implementation
6. Research/archive material

If two instructions conflict, stop and report the conflict rather than guessing.

---

## 5. RESEARCH IS NOT IMPLEMENTATION AUTHORITY

Research material is stored under:

```text
research/
├── RESEARCH_DOSSIER.md
└── SOURCES.md
```

These files contain supporting research and evidence.

Do NOT read the research dossier by default.

Do NOT use research material to independently change approved product requirements.

Research can inform a human decision, but implementation authority comes from the approved specification and current project state.

If you discover evidence that materially conflicts with the approved design:

1. Stop the affected task.
2. Describe the conflict.
3. Identify the affected requirement.
4. Do not silently redesign the project.
5. Wait for an updated specification or explicit human instruction.

---

## 6. PHASE CONTROL

The project has exactly ten implementation phases:

### C1 — Workspace & Configuration

Establish the actual development environment, project configuration, dependency definitions, test infrastructure, and required execution setup.

### C2 — Financial Test Fixtures

Create controlled synthetic financial models, valid fixtures, defective variants, and expected test outcomes.

### C3 — Workbook Inspection

Implement safe workbook loading, structural inspection, input validation, formula inspection, and unsupported-feature handling required by the approved specification.

### C4 — Deterministic Test Engine

Implement the approved financial assertions, tolerances, test execution, and structured pass/fail results.

### C5 — Scenario Execution

Implement controlled assumption changes, approved recalculation behaviour, scenario execution, and rerunning of financial assertions.

### C6 — Evidence-Linked Reports

Produce structured reports containing test status, expected conditions, observed values, relevant cell references, and explanations of failures.

### C7 — Security & Error Handling

Harden workbook processing, malformed-input handling, calculation failures, unsupported features, unsafe inputs, and source integrity.

### C8 — Benchmark & Regression Tests

Run the complete test suite, evaluate detection behaviour, false positives/negatives where measurable, regression behaviour, and benchmark results.

### C9 — Documentation & Release Preparation

Prepare installation instructions, usage documentation, examples, architecture documentation, limitations, licensing information, and release material.

### C10 — Final Audit & GitHub Publication

Perform the final repository audit, clean the repository, verify documentation and tests, inspect the final diff, and publish the approved release.

These phases are frozen.

Do not:

* reorder them
* merge them
* skip them
* add new implementation phases
* begin a later phase automatically
* perform work belonging to another phase

unless the human explicitly authorises a change.

---

## 7. ONE PHASE AT A TIME

Execution is strictly sequential.

At the beginning of every coding task:

1. Read `AGENTS.md`.
2. Read the relevant part of `PROJECT_STATE.md`.
3. Read only the relevant section of `BUILD_SPEC.md`.
4. Inspect only the source files and tests necessary for the authorised task.
5. Implement only that task.
6. Run the required verification.
7. Inspect the resulting diff.
8. Update project state with verified evidence.
9. Stop.

Never start the next phase automatically.

---

## 8. NO AUTONOMOUS SCOPE EXPANSION

Do not add features because they appear useful.

Do not introduce:

* dashboards
* web applications
* cloud infrastructure
* databases
* user accounts
* authentication
* APIs
* LLM integrations
* agent systems
* automatic model repair
* unnecessary GUI components
* external services
* telemetry
* analytics
* payment systems

unless they are explicitly approved in `BUILD_SPEC.md`.

The default engineering philosophy is:

**smallest system that proves the intended problem is solved.**

Avoid overengineering.

---

## 9. AI USAGE

AI coding tools are expected to perform a significant portion of routine implementation work.

They may:

* write code
* generate tests
* refactor code
* inspect errors
* propose local implementation fixes
* update documentation required by the current phase
* execute approved commands
* analyse test failures
* perform mechanical repository maintenance

They may NOT:

* redefine the product
* conduct independent market strategy
* change the target problem
* change approved financial rules
* remove acceptance criteria because they are inconvenient
* skip tests to save time
* declare unverified behaviour correct
* begin another phase
* silently change architectural decisions

AI-generated implementation is not evidence of correctness.

Only successful verification is evidence.

---

## 10. FINANCIAL CORRECTNESS

Financial logic is a high-risk part of this project.

Never invent a financial rule merely because it appears intuitively correct.

Financial assertions must be:

* explicitly defined
* deterministic where possible
* documented
* testable
* reproducible
* associated with clear expected behaviour
* validated against the approved specification

Examples of potential financial relationships include:

* balance-sheet balancing
* cash-flow consistency
* retained-earnings roll-forward
* debt roll-forward
* working-capital relationships
* scenario-driven directional behaviour
* transaction-model relationships

These are examples only.

They are NOT automatically approved requirements.

The authoritative financial rules are those defined in `BUILD_SPEC.md`.

When a financial rule is ambiguous:

**stop and report the ambiguity.**

Do not guess.

---

## 11. DETERMINISTIC-FIRST PRINCIPLE

The system should prefer deterministic computation and explicit assertions over probabilistic AI behaviour.

Where a rule can be expressed mathematically or structurally, prefer:

* deterministic calculations
* explicit assertions
* reproducible fixtures
* controlled inputs
* exact or tolerance-based comparisons
* structured evidence

Do not introduce an LLM merely because the project contains the word "AI" in its broader portfolio context.

If AI does not materially improve the approved problem, it should not be added.

---

## 12. REPRODUCIBILITY

A test result must be reproducible.

Where practical, tests should record:

* input state
* scenario inputs
* expected condition
* observed result
* tolerance
* relevant workbook/sheet/cell
* test identifier
* execution result
* error or limitation

Avoid tests that depend unnecessarily on:

* current time
* network availability
* external APIs
* random uncontrolled data
* local machine state
* proprietary files

Synthetic fixtures should be deterministic.

---

## 13. SOURCE WORKBOOK SAFETY

Financial workbooks must be treated as untrusted input.

Never assume that an input workbook is safe.

The implementation must follow the security requirements defined in `BUILD_SPEC.md`.

General principles:

* never overwrite the original source workbook
* never execute macros automatically
* never follow external links automatically
* never execute arbitrary workbook-derived code
* isolate or constrain recalculation where required
* validate file types and inputs
* fail safely on malformed files
* avoid leaking workbook data into logs unnecessarily

Security requirements must become concrete implementation and test requirements during the authorised security phase.

---

## 14. ERROR HANDLING

Errors must be explicit.

Never silently convert:

* calculation failures
* unsupported workbook features
* malformed inputs
* missing values
* missing formulas
* failed assertions

into a normal "PASS".

A test that cannot be evaluated is not equivalent to a passed test.

The system must distinguish, where required by the specification, between states such as:

* PASS
* FAIL
* ERROR
* UNSUPPORTED
* INCOMPLETE

Do not invent additional status semantics unless approved.

---

## 15. TESTING REQUIREMENTS

Every implementation phase must have appropriate verification.

At minimum:

* targeted tests for the changed behaviour
* regression tests where existing behaviour could be affected
* full test suite at appropriate milestones
* negative/error-path tests for safety-critical behaviour

Never remove a failing test merely to make the suite green.

If a test expectation is genuinely incorrect, document why and obtain approval through the specification/state workflow before changing it.

A green test suite does not automatically prove product correctness.

---

## 16. BENCHMARKING

The project should eventually provide measurable evidence of what it detects and what it does not detect.

Benchmarking must distinguish between:

* true detections
* missed defects
* false positives
* unsupported cases
* incomplete execution

Do not manufacture benchmark numbers.

Do not report an impressive detection percentage unless the test population and methodology are clearly defined.

Synthetic benchmark results must be labelled as synthetic.

Real-world validation must be clearly separated from synthetic testing.

---

## 17. TOKEN AND CONTEXT EFFICIENCY

Coding agents must minimise unnecessary context consumption.

Do not:

* reread the entire repository unnecessarily
* reread unrelated documentation
* inspect unrelated source files
* reproduce entire files when a targeted section is sufficient
* regenerate existing information unnecessarily

Preferred workflow:

```text
Read relevant state
→ Read relevant specification
→ Inspect required files
→ Implement
→ Run targeted tests
→ Inspect diff
→ Run required broader verification
→ Update state
→ Stop
```

Efficiency must never justify skipping necessary verification.

---

## 18. FILE MODIFICATION DISCIPLINE

Before modifying a file:

* understand why the file is relevant to the authorised task
* inspect the required surrounding context
* preserve unrelated behaviour
* avoid opportunistic refactoring

Do not modify unrelated files merely because they could be improved.

Keep changes narrowly scoped.

---

## 19. DEPENDENCY DISCIPLINE

Do not install dependencies unless they are authorised by the current phase/specification.

Before adding a dependency, verify that it is actually necessary.

Prefer:

* standard library functionality where sufficient
* small, well-maintained dependencies
* local-first operation
* reproducible dependency versions where appropriate

Do not introduce a dependency merely for convenience.

Dependency changes must be visible in the project diff.

---

## 20. NETWORK AND EXTERNAL SERVICES

The default project architecture is local-first.

Do not introduce network communication unless explicitly approved.

No external API should become a hidden runtime dependency.

If an external service is required by a later approved specification:

* document why
* define failure behaviour
* define data boundaries
* define security implications
* test offline/error behaviour where appropriate

---

## 21. DATA PRIVACY

Financial workbooks may contain confidential information.

The system should minimise data exposure.

Do not:

* upload workbook contents to external services without explicit approval
* transmit workbook data unnecessarily
* place sensitive workbook contents into logs
* include real confidential financial data in public fixtures
* commit credentials or secrets

Public examples must use synthetic or appropriately sanitised data.

---

## 22. GIT DISCIPLINE

The repository must remain clean and reviewable.

Do not commit:

* secrets
* credentials
* private financial files
* temporary files
* virtual environments
* caches
* compiled Python files
* machine-specific configuration
* unnecessary generated artifacts

Before release:

* inspect `git status`
* inspect the diff
* inspect tracked files
* verify documentation
* verify tests
* verify no sensitive material exists

Do not publish until C10 is explicitly authorised.

---

## 23. DOCUMENTATION DISCIPLINE

Documentation must describe verified behaviour.

Never document:

* unimplemented features
* untested guarantees
* unsupported capabilities as supported
* hypothetical benchmark results as actual results

If a limitation exists, document the limitation.

Accuracy is more important than marketing language.

---

## 24. STOP CONDITIONS

Immediately stop and report if:

* the specification is ambiguous
* two project documents conflict
* an acceptance criterion cannot be met
* a required dependency cannot be safely used
* a financial rule is unclear
* a security requirement cannot be satisfied
* a test reveals an unexpected architectural problem
* implementation would require changing the approved product scope
* the current phase depends on unfinished work from another phase
* a later-phase feature appears necessary to complete the current phase

Do not work around a blocking requirement silently.

---

## 25. DEFINITION OF DONE

A phase is NOT complete because code was written.

A phase is complete only when:

1. The authorised work has been implemented.
2. Relevant tests have been created or updated.
3. Required tests pass.
4. Required error paths have been verified.
5. The implementation matches the approved specification.
6. The resulting diff has been inspected.
7. Documentation/state has been updated where required.
8. No known blocker remains within the phase.
9. Completion evidence has been recorded in `PROJECT_STATE.md`.

Only then may the phase be marked complete.

---

## 26. PROJECT STATE MANAGEMENT

`PROJECT_STATE.md` is the operational ledger.

At phase boundaries, record:

* current phase
* completed work
* files changed
* tests executed
* exact test results
* verification evidence
* known limitations
* unresolved issues
* decisions requiring human approval
* next authorised action

Do not fabricate progress.

If something was not verified, mark it as unverified.

---

## 27. FINAL RESPONSE FORMAT

At the end of each authorised coding task, report concisely:

```text
PHASE:
[authorised phase]

CHANGES:
[what was changed]

VERIFICATION:
[tests/commands/results]

ISSUES:
[remaining issues or "None"]

STATE:
[updated / not updated]

NEXT AUTHORISED ACTION:
[describe it, but do not execute it]
```

Do not provide unnecessary narrative.

Do not claim success without evidence.

Do not begin the next action automatically.

---

## 28. CURRENT PROJECT STATUS

At the time these instructions were created:

* the repository structure has been created
* no implementation has started
* no source code exists
* no dependencies have been installed
* C1 has NOT started
* C2–C10 have NOT started

The next activity is specification and instruction preparation.

Coding begins only when the human explicitly authorises C1.

---

## 29. NON-NEGOTIABLE PRINCIPLE

The project is intended to demonstrate a real engineering solution to a narrowly defined financial-model testing problem.

Do not optimise for:

* number of features
* number of files
* lines of code
* complexity
* AI involvement
* visual polish

Optimise for:

**problem validity → financial correctness → reproducibility → measurable testing value → security → simplicity.**

When forced to choose between impressive complexity and a smaller verifiable solution, choose the smaller verifiable solution.
