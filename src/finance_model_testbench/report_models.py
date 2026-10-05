"""
Data models for Phase C6 — Evidence-Linked Reports.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class OverallOutcome(str, Enum):
    """Overall outcome status for a testbench execution report."""
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    UNSUPPORTED = "UNSUPPORTED"
    INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True)
class ReportMetadata:
    """
    Metadata associated with a testbench execution report.

    Attributes:
        schema_version: Version of the report schema (e.g., "1.0.0").
        report_id: Deterministic hash identifying this execution configuration.
        source_filename: Basename of the target financial model workbook file.
        source_sha256: SHA-256 hash of the target workbook file.
        scenario_id: Identifier of the executed scenario ("BASELINE" if none).
        inputs_applied: Mapping of cell target strings to applied values.
        timestamp: Optional execution timestamp (defaults to None for byte determinism).
    """
    schema_version: str
    report_id: str
    source_filename: str
    source_sha256: str
    scenario_id: str
    inputs_applied: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "report_id": self.report_id,
            "source_filename": self.source_filename,
            "source_sha256": self.source_sha256,
            "scenario_id": self.scenario_id,
            "inputs_applied": dict(self.inputs_applied),
        }
        if self.timestamp is not None:
            d["timestamp"] = self.timestamp
        return d


@dataclass(frozen=True)
class TestEvidence:
    """
    Evidence details for an individual assertion result within a report.

    Attributes:
        test_id: Unique assertion test identifier.
        description: Human-readable description of the assertion hypothesis.
        assertion_type: Category of assertion (EQUALITY, DIFFERENCE, SUM_EQUALITY).
        status: Assertion outcome status (PASS, FAIL, ERROR, UNSUPPORTED, INCOMPLETE).
        expected: Expected value or baseline relationship operand value.
        observed: Observed calculated or resolved value.
        difference: Calculated numerical difference (observed - expected).
        tolerance_type: Declared tolerance type (EXACT, ABSOLUTE, RELATIVE).
        tolerance_value: Declared numerical tolerance threshold.
        referenced_cells: List of cell coordinate dictionaries with sheet and coordinate details.
        explanation: Clear, concise explanation of the assertion outcome.
        limitations: Optional diagnostic notes regarding value resolution or recalculation.
    """
    test_id: str
    description: str
    assertion_type: str
    status: str
    expected: Optional[float]
    observed: Optional[float]
    difference: Optional[float]
    tolerance_type: str
    tolerance_value: float
    referenced_cells: Tuple[Dict[str, str], ...] = field(default_factory=tuple)
    explanation: str = ""
    limitations: Optional[str] = None

    def __post_init__(self) -> None:
        if isinstance(self.referenced_cells, list):
            object.__setattr__(self, "referenced_cells", tuple(self.referenced_cells))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "description": self.description,
            "assertion_type": self.assertion_type,
            "status": self.status,
            "expected": self.expected,
            "observed": self.observed,
            "difference": self.difference,
            "tolerance_type": self.tolerance_type,
            "tolerance_value": self.tolerance_value,
            "referenced_cells": [dict(c) for c in self.referenced_cells],
            "explanation": self.explanation,
            "limitations": self.limitations,
        }


@dataclass(frozen=True)
class ReportSummary:
    """
    Aggregated summary metrics for a test execution run.
    """
    total_assertions: int
    pass_count: int
    fail_count: int
    error_count: int
    unsupported_count: int
    incomplete_count: int
    overall_outcome: OverallOutcome

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_assertions": self.total_assertions,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "error_count": self.error_count,
            "unsupported_count": self.unsupported_count,
            "incomplete_count": self.incomplete_count,
            "overall_outcome": self.overall_outcome.value,
        }


@dataclass(frozen=True)
class TestbenchReport:
    """
    Complete structured evidence-linked report for a financial model test execution.
    """
    metadata: ReportMetadata
    summary: ReportSummary
    evidence: Tuple[TestEvidence, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if isinstance(self.evidence, list):
            object.__setattr__(self, "evidence", tuple(self.evidence))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "summary": self.summary.to_dict(),
            "evidence": [ev.to_dict() for ev in self.evidence],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serializes report to a deterministic JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Generates clean human-readable Markdown report representation."""
        lines = [
            f"# Financial Model Testbench Report",
            f"",
            f"## Executive Summary",
            f"",
            f"- **Overall Outcome:** `{self.summary.overall_outcome.value}`",
            f"- **Total Assertions:** `{self.summary.total_assertions}`",
            f"- **Passed:** `{self.summary.pass_count}` | **Failed:** `{self.summary.fail_count}` | **Errors:** `{self.summary.error_count}` | **Unsupported:** `{self.summary.unsupported_count}` | **Incomplete:** `{self.summary.incomplete_count}`",
            f"",
            f"## Execution Metadata",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| **Report ID** | `{self.metadata.report_id}` |",
            f"| **Source File** | `{_escape_markdown(self.metadata.source_filename)}` |",
            f"| **Source SHA-256** | `{self.metadata.source_sha256}` |",
            f"| **Scenario ID** | `{_escape_markdown(self.metadata.scenario_id)}` |",
            f"| **Schema Version** | `{self.metadata.schema_version}` |",
        ]

        if self.metadata.timestamp:
            lines.append(f"| **Timestamp** | `{self.metadata.timestamp}` |")

        if self.metadata.inputs_applied:
            lines.extend([
                f"",
                f"### Scenario Inputs Applied",
                f"",
                f"| Target Cell | Applied Value |",
                f"|-------------|---------------|",
            ])
            for k, v in sorted(self.metadata.inputs_applied.items()):
                lines.append(f"| `{_escape_markdown(k)}` | `{_escape_markdown(str(v))}` |")

        lines.extend([
            f"",
            f"## Assertion Evidence Details",
            f"",
        ])

        for ev in self.evidence:
            badge = f"**[{ev.status}]**"
            lines.append(f"### {badge} {ev.test_id}: {_escape_markdown(ev.description)}")
            lines.append(f"")
            lines.append(f"- **Assertion Type:** `{ev.assertion_type}`")
            lines.append(f"- **Status:** `{ev.status}`")
            lines.append(f"- **Tolerance:** `{ev.tolerance_type}` ({ev.tolerance_value})")

            if ev.expected is not None:
                lines.append(f"- **Expected Value:** `{ev.expected}`")
            if ev.observed is not None:
                lines.append(f"- **Observed Value:** `{ev.observed}`")
            if ev.difference is not None:
                lines.append(f"- **Difference:** `{ev.difference}`")

            if ev.referenced_cells:
                cell_strs = [f"`'{c.get('sheet_name', '')}'!{c.get('coordinate', '')}`" for c in ev.referenced_cells]
                lines.append(f"- **Referenced Cells:** {', '.join(cell_strs)}")

            lines.append(f"- **Explanation:** {_escape_markdown(ev.explanation)}")

            if ev.limitations:
                lines.append(f"- **Limitations:** *{_escape_markdown(ev.limitations)}*")

            lines.append(f"")

        return "\n".join(lines)


def _escape_markdown(text: str) -> str:
    """
    Escapes Markdown control characters in user/workbook-derived strings to prevent
    structural injection into the generated report.

    Characters handled:
    - Backtick (`): replaced with single quote to prevent inline-code injection
    - Pipe (|): escaped as \\| to prevent table-cell boundary injection
    - Newline (\n, \r): collapsed to space to prevent heading/block injection
    - Hash (#): escaped as &#35; to prevent heading-level injection at line start
    - Asterisk (*) and underscore (_): escaped to prevent bold/italic injection

    Security note: this function prevents structural injection in the specific
    Markdown patterns used by this report generator. It does not sanitize for
    all possible Markdown renderers or HTML output contexts.
    """
    if not text:
        return ""
    # Newlines first so subsequent character replacements apply to flattened text
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    # Structural injection characters
    text = text.replace("`", "'")          # inline-code injection
    text = text.replace("|", "\\|")        # table-cell boundary injection
    text = text.replace("#", "&#35;")      # heading injection
    text = text.replace("*", "&#42;")      # bold/italic injection
    text = text.replace("_", "&#95;")      # italic/emphasis injection
    return text
