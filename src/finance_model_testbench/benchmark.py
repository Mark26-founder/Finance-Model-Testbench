"""C8 benchmark and regression orchestration over the existing testbench."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

from finance_model_testbench.assertion_models import (
    AssertionStatus, AssertionType, CellReference, TestDefinition,
    absolute_tolerance,
)
from finance_model_testbench.scenario_models import ScenarioDefinition, ScenarioInput
from finance_model_testbench.scenario_runner import ScenarioRunner


STATUSES = {status.value for status in AssertionStatus}


@dataclass(frozen=True)
class BenchmarkCase:
    benchmark_id: str
    fixture_id: str
    relative_path: str
    defect_category: Optional[str]
    assertion: TestDefinition
    expected_status: str
    rationale: str
    supported: bool = True
    scenario: Optional[ScenarioDefinition] = None

    def __post_init__(self) -> None:
        if self.expected_status not in STATUSES:
            raise ValueError(f"Unknown expected status: {self.expected_status}")


@dataclass(frozen=True)
class BenchmarkResult:
    benchmark_id: str
    fixture_id: str
    fixture: str
    fixture_sha256: str
    defect_category: Optional[str]
    expected_status: str
    actual_status: str
    benchmark_result: str
    supported: bool
    scenario_id: Optional[str]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _root() -> Path:
    """Locate repository fixtures for source-tree and installed-package use."""
    working_root = Path.cwd()
    if (working_root / "examples" / "fixtures" / "manifests" / "ground_truth_manifest.json").is_file():
        return working_root
    return Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _definitions() -> dict[str, TestDefinition]:
    tol = absolute_tolerance(0.01)
    return {
        "bs": TestDefinition("TD_BS_BALANCE", "Balance Sheet identity", AssertionType.EQUALITY,
            (CellReference("Balance Sheet", "C5"), CellReference("Balance Sheet", "C12")), tol),
        "re": TestDefinition("TD_RE_ROLLFORWARD", "Retained Earnings roll-forward", AssertionType.DIFFERENCE,
            (CellReference("Balance Sheet", "C10"), CellReference("Balance Sheet", "B10")), tol, expected_value=112.5),
        "cf": TestDefinition("TD_CF_LINK", "Cash Flow depreciation linkage", AssertionType.EQUALITY,
            (CellReference("Cash Flow Statement", "B3"), CellReference("Income Statement", "C5")), tol),
    }


def benchmark_cases() -> tuple[BenchmarkCase, ...]:
    defs = _definitions()
    return (
        BenchmarkCase("BM_VALID_001", "FIX_VALID_001", "examples/fixtures/valid/valid_three_statement.xlsx", None, defs["bs"], "PASS", "Valid model must balance."),
        BenchmarkCase("BM_DEF_BS_001", "FIX_DEF_001", "examples/fixtures/defective/defective_balance_sheet_imbalance.xlsx", "STATEMENT_INTEGRITY", defs["bs"], "FAIL", "Manifest defines an artificial assets offset."),
        BenchmarkCase("BM_DEF_RE_001", "FIX_DEF_002", "examples/fixtures/defective/defective_retained_earnings_rollforward.xlsx", "ROLL_FORWARD", defs["re"], "FAIL", "Manifest defines an unrecorded dividend offset."),
        BenchmarkCase("BM_DEF_LINK_001", "FIX_DEF_003", "examples/fixtures/defective/defective_cash_flow_linkage.xlsx", "CROSS_STATEMENT_LINK", defs["cf"], "FAIL", "Manifest defines a hardcoded depreciation add-back."),
        BenchmarkCase("BM_SCENARIO_001", "FIX_SCEN_001", "examples/fixtures/scenarios/scenario_three_statement.xlsx", "SCENARIO_BEHAVIOUR", defs["bs"], "PASS", "A controlled revenue-growth scenario preserves balance.", scenario=ScenarioDefinition("SCEN_REV_GROWTH_10", "Increase revenue growth", (ScenarioInput(CellReference("Assumptions", "B2"), 0.10),))),
    )


class BenchmarkRunner:
    schema_version = "1.0"

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root) if root else _root()
        self.scenario_runner = ScenarioRunner()

    def run(self, cases: Optional[Sequence[BenchmarkCase]] = None) -> dict[str, Any]:
        output: list[BenchmarkResult] = []
        for case in cases or benchmark_cases():
            path = self.root / case.relative_path
            before = _sha256(path)
            if not case.supported:
                actual = "UNSUPPORTED"
            else:
                execution = self.scenario_runner.run(str(path), [case.assertion], scenario=case.scenario)
                actual = execution.assertion_results[0].status.value
            after = _sha256(path)
            if before != after:
                raise RuntimeError(f"Source fixture modified: {case.relative_path}")
            output.append(BenchmarkResult(case.benchmark_id, case.fixture_id, case.relative_path, before, case.defect_category, case.expected_status, actual, "PASS" if actual == case.expected_status else "FAIL", case.supported, case.scenario.scenario_id if case.scenario else None, case.rationale))
        supported = [r for r in output if r.supported]
        correct = [r for r in supported if r.benchmark_result == "PASS"]
        expected_pass = [r for r in output if r.expected_status == "PASS"]
        expected_fail = [r for r in output if r.expected_status == "FAIL"]
        false_positive = [r for r in expected_pass if r.actual_status != "PASS"]
        return {"schema_version": self.schema_version, "benchmark_type": "synthetic_internal_correctness", "cases": [r.to_dict() for r in output], "metrics": {"total_cases": len(output), "supported_cases": len(supported), "unsupported_cases": len(output)-len(supported), "expected_pass_cases": len(expected_pass), "expected_fail_cases": len(expected_fail), "correctly_classified_cases": len(correct), "incorrectly_classified_cases": len(supported)-len(correct), "accuracy": (len(correct)/len(supported) if supported else None), "known_defect_detections": sum(r.expected_status == "FAIL" and r.actual_status == "FAIL" for r in output), "false_positive_count": len(false_positive)}, "reproducibility": {"source_fixture_hashes": {r.fixture_id: r.fixture_sha256 for r in output}, "canonical": True}}

    @staticmethod
    def to_json(result: dict[str, Any]) -> str:
        return json.dumps(result, indent=2, sort_keys=True) + "\n"

    @staticmethod
    def to_markdown(result: dict[str, Any]) -> str:
        m = result["metrics"]
        lines = ["# C8 Benchmark Results", "", "Synthetic internal correctness benchmark.", "", "## Detection matrix", "", "| Benchmark | Expected | Actual | Result | Defect |", "|---|---|---|---|---|"]
        lines += [f"| {c['benchmark_id']} | {c['expected_status']} | {c['actual_status']} | {c['benchmark_result']} | {c['defect_category'] or 'None'} |" for c in result["cases"]]
        lines += ["", "## Metrics", "", f"- Cases: {m['total_cases']} ({m['supported_cases']} supported, {m['unsupported_cases']} unsupported)", f"- Correct classifications: {m['correctly_classified_cases']}", f"- Known defect detections: {m['known_defect_detections']}", f"- False positives: {m['false_positive_count']}", f"- Accuracy: {m['accuracy']}", "", "## Limitations", "", "The corpus is synthetic and small; it does not establish real-world detection rates. Tested defects do not represent every financial-model defect. Formula correctness is not business correctness, Excel semantics may differ from the calculation engine, unsupported features may exist, and professional financial judgment remains necessary.", ""]
        return "\n".join(lines)


def load_ground_truth(path: Optional[Path] = None) -> dict[str, Any]:
    manifest = path or (_root() / "examples/fixtures/manifests/ground_truth_manifest.json")
    data = json.loads(Path(manifest).read_text(encoding="utf-8"))
    if not isinstance(data.get("fixtures"), list):
        raise ValueError("Ground-truth manifest must contain a fixtures list")
    return data
