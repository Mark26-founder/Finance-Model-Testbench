# C8 — Benchmark and Regression Tests

## Purpose

C8 is a small, synthetic internal correctness benchmark. It executes the existing C4 assertions through the C5 scenario runner and compares actual statuses with explicit ground truth from the C2 fixture manifest.

## Corpus and ground truth

The corpus contains one valid model, three defective models (`STATEMENT_INTEGRITY`, `ROLL_FORWARD`, and `CROSS_STATEMENT_LINK`), and one controlled scenario. Each case has an explicit benchmark ID, fixture ID, assertion, expected status, rationale, and fixture hash. The manifest and defect taxonomy remain the independent fixture definitions.

## Execution and outputs

`BenchmarkRunner` performs recalculation and assertion execution using existing project components, checks source hashes before and after execution, and emits deterministic JSON plus a Markdown detection matrix. `expected_status` is the ground-truth expectation; `actual_status` is the assertion result; `benchmark_result` records whether they match.

## Metrics and interpretation

Reported metrics include total, supported and unsupported cases, expected PASS/FAIL populations, correct and incorrect classifications, accuracy over supported cases, known defect detections, and valid-model false positives. A small synthetic corpus demonstrates only that these tested cases were handled correctly; it does not provide a general real-world detection rate.

## Reproducibility and limitations

The canonical JSON excludes timestamps and absolute paths. Repeated execution is expected to produce identical output. The corpus is synthetic and limited. Tested defects do not represent every financial-model defect; formula correctness is not business correctness; calculation-engine semantics may differ from Microsoft Excel; unsupported Excel features may exist; and professional financial judgment remains necessary. C8 is an internal correctness/regression benchmark, not a commercial comparison.
