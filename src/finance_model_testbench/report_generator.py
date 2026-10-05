"""
Report generator for Phase C6 — Evidence-Linked Reports.
"""

import hashlib
import os
from typing import Dict, List, Optional, Sequence

from finance_model_testbench.assertion_models import AssertionResult, AssertionStatus, TestDefinition
from finance_model_testbench.exceptions import InvalidInputError
from finance_model_testbench.report_models import (
    OverallOutcome,
    ReportMetadata,
    ReportSummary,
    TestbenchReport,
    TestEvidence,
)
from finance_model_testbench.scenario_models import RecalculationStatus, ScenarioExecutionResult

REPORT_SCHEMA_VERSION = "1.0.0"


class ReportGenerator:
    """
    Transforms C4 assertion results and C5 scenario execution results into structured,
    auditable, evidence-linked reports.
    """

    def generate_report(
        self,
        execution_result: ScenarioExecutionResult,
        test_definitions: Sequence[TestDefinition],
        timestamp: Optional[str] = None,
    ) -> TestbenchReport:
        """
        Generates a deterministic TestbenchReport from a ScenarioExecutionResult.

        Args:
            execution_result: ScenarioExecutionResult object produced by ScenarioRunner.
            test_definitions: Sequence of TestDefinition objects evaluated during execution.
            timestamp: Optional execution timestamp string (defaults to None for byte determinism).

        Returns:
            TestbenchReport object containing metadata, summary metrics, and test evidence details.
        """
        if not isinstance(execution_result, ScenarioExecutionResult):
            raise InvalidInputError("execution_result must be a ScenarioExecutionResult instance.")

        if not test_definitions:
            raise InvalidInputError("test_definitions sequence cannot be empty.")

        for td in test_definitions:
            if not isinstance(td, TestDefinition):
                raise InvalidInputError(f"All elements of test_definitions must be TestDefinition, got {type(td)}.")

        # Map test definitions by test_id for fast lookup
        def_map: Dict[str, TestDefinition] = {td.test_id: td for td in test_definitions}

        # Deterministic Report ID derived from source SHA-256, scenario_id, and sorted test_ids
        test_ids_key = ",".join(sorted(def_map.keys()))
        hash_payload = f"{execution_result.source_sha256}:{execution_result.scenario_id}:{test_ids_key}"
        report_id = f"REP_{hashlib.sha256(hash_payload.encode('utf-8')).hexdigest()[:16]}"

        source_filename = os.path.basename(execution_result.source_file)

        # Process assertion evidence items
        evidence_list: List[TestEvidence] = []
        pass_cnt = 0
        fail_cnt = 0
        error_cnt = 0
        unsupported_cnt = 0
        incomplete_cnt = 0

        for a_res in execution_result.assertion_results:
            status_val = a_res.status.value

            if a_res.status == AssertionStatus.PASS:
                pass_cnt += 1
            elif a_res.status == AssertionStatus.FAIL:
                fail_cnt += 1
            elif a_res.status == AssertionStatus.ERROR:
                error_cnt += 1
            elif a_res.status == AssertionStatus.UNSUPPORTED:
                unsupported_cnt += 1
            elif a_res.status == AssertionStatus.INCOMPLETE:
                incomplete_cnt += 1

            td = def_map.get(a_res.test_id)
            desc = td.description if td else ""

            # Extract referenced cells and notes/limitations
            ref_cells: List[Dict[str, str]] = []
            notes: List[str] = []

            for rv in a_res.resolved:
                ref_cells.append({
                    "sheet_name": rv.reference.sheet_name,
                    "coordinate": rv.reference.coordinate,
                    "label": rv.reference.label or "",
                })
                if rv.note:
                    notes.append(rv.note)

            limitation_str = "; ".join(dict.fromkeys(notes)) if notes else None

            ev = TestEvidence(
                test_id=a_res.test_id,
                description=desc,
                assertion_type=a_res.assertion_type.value,
                status=status_val,
                expected=a_res.expected,
                observed=a_res.observed,
                difference=a_res.difference,
                tolerance_type=a_res.tolerance.tolerance_type.value,
                tolerance_value=a_res.tolerance.tolerance_value,
                referenced_cells=tuple(ref_cells),
                explanation=a_res.message,
                limitations=limitation_str,
            )
            evidence_list.append(ev)

        # Check recalculation status impact on overall outcome
        recalc_err = (execution_result.recalculation_status == RecalculationStatus.ERROR)
        recalc_unsupported = (execution_result.recalculation_status == RecalculationStatus.UNSUPPORTED)
        recalc_incomplete = (execution_result.recalculation_status == RecalculationStatus.INCOMPLETE)

        # Overall outcome precedence rules
        if error_cnt > 0 or recalc_err:
            overall_outcome = OverallOutcome.ERROR
        elif fail_cnt > 0:
            overall_outcome = OverallOutcome.FAIL
        elif unsupported_cnt > 0 or recalc_unsupported:
            overall_outcome = OverallOutcome.UNSUPPORTED
        elif incomplete_cnt > 0 or recalc_incomplete:
            overall_outcome = OverallOutcome.INCOMPLETE
        elif pass_cnt > 0 and pass_cnt == len(execution_result.assertion_results):
            overall_outcome = OverallOutcome.PASS
        else:
            overall_outcome = OverallOutcome.INCOMPLETE

        summary = ReportSummary(
            total_assertions=len(execution_result.assertion_results),
            pass_count=pass_cnt,
            fail_count=fail_cnt,
            error_count=error_cnt,
            unsupported_count=unsupported_cnt,
            incomplete_count=incomplete_cnt,
            overall_outcome=overall_outcome,
        )

        metadata = ReportMetadata(
            schema_version=REPORT_SCHEMA_VERSION,
            report_id=report_id,
            source_filename=source_filename,
            source_sha256=execution_result.source_sha256,
            scenario_id=execution_result.scenario_id,
            inputs_applied=execution_result.inputs_applied,
            timestamp=timestamp,
        )

        return TestbenchReport(
            metadata=metadata,
            summary=summary,
            evidence=tuple(evidence_list),
        )
