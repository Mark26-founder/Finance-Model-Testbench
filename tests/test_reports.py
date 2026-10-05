"""
Comprehensive C6 Test Suite — Evidence-Linked Reports.
"""

import hashlib
import json
import os
import pytest

from finance_model_testbench import (
    AssertionResult,
    AssertionStatus,
    AssertionType,
    CellReference,
    InvalidInputError,
    OverallOutcome,
    RecalculationStatus,
    ReportGenerator,
    ReportMetadata,
    ReportSummary,
    ScenarioDefinition,
    ScenarioExecutionResult,
    ScenarioInput,
    ScenarioRunner,
    TestDefinition,
    TestEvidence,
    TestbenchReport,
    absolute_tolerance,
)


@pytest.fixture
def valid_fixture_path():
    return os.path.abspath(os.path.join("examples", "fixtures", "valid", "valid_three_statement.xlsx"))


@pytest.fixture
def bs_defective_path():
    return os.path.abspath(os.path.join("examples", "fixtures", "defective", "defective_balance_sheet_imbalance.xlsx"))


@pytest.fixture
def bs_balance_test_def():
    return TestDefinition(
        test_id="TD_BS_BALANCE",
        description="Balance Sheet identity: Total Assets == Total Liabilities + Equity",
        assertion_type=AssertionType.EQUALITY,
        operands=[
            CellReference("Balance Sheet", "C5", label="Total Assets"),
            CellReference("Balance Sheet", "C12", label="Total Liabilities & Equity"),
        ],
        tolerance=absolute_tolerance(0.01),
    )


@pytest.fixture
def re_rollforward_test_def():
    return TestDefinition(
        test_id="TD_RE_ROLLFORWARD",
        description="Retained Earnings rollforward: Ending RE - Beginning RE == Net Income",
        assertion_type=AssertionType.DIFFERENCE,
        operands=[
            CellReference("Balance Sheet", "C10", label="Ending Retained Earnings"),
            CellReference("Balance Sheet", "B10", label="Beginning Retained Earnings"),
        ],
        expected_value=112.5,
        tolerance=absolute_tolerance(0.01),
    )


def compute_sha256(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


# ===========================================================================
# 1. Report Generation & JSON Serialization Tests
# ===========================================================================


class TestReportGeneratorJSON:
    def test_generate_json_report_from_valid_execution(self, valid_fixture_path, bs_balance_test_def):
        runner = ScenarioRunner()
        exec_res = runner.run(valid_fixture_path, [bs_balance_test_def])

        generator = ReportGenerator()
        report = generator.generate_report(exec_res, [bs_balance_test_def])

        assert isinstance(report, TestbenchReport)
        assert report.summary.overall_outcome == OverallOutcome.PASS
        assert report.summary.total_assertions == 1
        assert report.summary.pass_count == 1
        assert report.summary.fail_count == 0

        # JSON serialization check
        json_str = report.to_json()
        data = json.loads(json_str)

        assert data["metadata"]["source_filename"] == "valid_three_statement.xlsx"
        assert data["metadata"]["source_sha256"] == exec_res.source_sha256
        assert data["summary"]["overall_outcome"] == "PASS"
        assert len(data["evidence"]) == 1
        assert data["evidence"][0]["test_id"] == "TD_BS_BALANCE"
        assert data["evidence"][0]["observed"] == 1012.5
        assert data["evidence"][0]["expected"] == 1012.5

    def test_json_preserves_numeric_precision(self, valid_fixture_path, bs_balance_test_def):
        runner = ScenarioRunner()
        exec_res = runner.run(valid_fixture_path, [bs_balance_test_def])

        generator = ReportGenerator()
        report = generator.generate_report(exec_res, [bs_balance_test_def])
        data = json.loads(report.to_json())

        # Assert floats are not rounded or stringified in JSON output
        assert isinstance(data["evidence"][0]["observed"], float)
        assert data["evidence"][0]["observed"] == 1012.5


# ===========================================================================
# 2. Status & Precedence Rules Tests
# ===========================================================================


class TestOverallOutcomePrecedence:
    def test_outcome_is_fail_when_any_assertion_fails(self, bs_defective_path, bs_balance_test_def, re_rollforward_test_def):
        runner = ScenarioRunner()
        exec_res = runner.run(bs_defective_path, [bs_balance_test_def, re_rollforward_test_def])

        generator = ReportGenerator()
        report = generator.generate_report(exec_res, [bs_balance_test_def, re_rollforward_test_def])

        assert report.summary.fail_count == 1
        assert report.summary.pass_count == 1
        assert report.summary.overall_outcome == OverallOutcome.FAIL

    def test_outcome_is_error_when_recalculation_fails(self, valid_fixture_path, bs_balance_test_def):
        # Create a synthetic error execution result
        runner = ScenarioRunner()
        base_res = runner.run(valid_fixture_path, [bs_balance_test_def])

        err_exec_res = ScenarioExecutionResult(
            scenario_id=base_res.scenario_id,
            source_file=base_res.source_file,
            source_sha256=base_res.source_sha256,
            recalculation_status=RecalculationStatus.ERROR,
            recalculation_message="Recalculation encountered formula evaluation error",
            assertion_results=base_res.assertion_results,
            inputs_applied=base_res.inputs_applied,
        )

        generator = ReportGenerator()
        report = generator.generate_report(err_exec_res, [bs_balance_test_def])

        assert report.summary.overall_outcome == OverallOutcome.ERROR


# ===========================================================================
# 3. Scenario & Provenance Evidence Tests
# ===========================================================================


class TestScenarioEvidence:
    def test_scenario_inputs_and_provenance_preserved(self, valid_fixture_path, bs_balance_test_def):
        runner = ScenarioRunner()
        scenario = ScenarioDefinition(
            scenario_id="SCEN_REPORT_TEST",
            description="Revenue growth test scenario",
            inputs=[ScenarioInput(cell=CellReference("Assumptions", "B2"), value=0.10)],
        )

        exec_res = runner.run(valid_fixture_path, [bs_balance_test_def], scenario=scenario)

        generator = ReportGenerator()
        report = generator.generate_report(exec_res, [bs_balance_test_def])

        assert report.metadata.scenario_id == "SCEN_REPORT_TEST"
        assert "'Assumptions'!B2" in report.metadata.inputs_applied
        assert report.metadata.inputs_applied["'Assumptions'!B2"] == "0.1"


# ===========================================================================
# 4. Markdown Generation & Security Sanitization Tests
# ===========================================================================


class TestMarkdownReportGeneration:
    def test_generate_markdown_report(self, valid_fixture_path, bs_balance_test_def):
        runner = ScenarioRunner()
        exec_res = runner.run(valid_fixture_path, [bs_balance_test_def])

        generator = ReportGenerator()
        report = generator.generate_report(exec_res, [bs_balance_test_def])
        md = report.to_markdown()

        assert "# Financial Model Testbench Report" in md
        assert "**Overall Outcome:** `PASS`" in md
        assert "TD_BS_BALANCE" in md
        assert "Balance Sheet identity" in md

    def test_markdown_sanitizes_injection_strings(self, valid_fixture_path):
        # Create test def with malicious Markdown characters in description
        test_def_malicious = TestDefinition(
            test_id="TD_MALICIOUS",
            description="Malicious `code` | table | injection\nNew line attack",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("Balance Sheet", "C5"),
                CellReference("Balance Sheet", "C12"),
            ],
            tolerance=absolute_tolerance(0.01),
        )

        runner = ScenarioRunner()
        exec_res = runner.run(valid_fixture_path, [test_def_malicious])

        generator = ReportGenerator()
        report = generator.generate_report(exec_res, [test_def_malicious])
        md = report.to_markdown()

        # Verify backticks replaced, pipes escaped, newlines removed
        assert "`code`" not in md
        assert "'code'" in md
        assert "New line attack" in md


# ===========================================================================
# 5. Determinism & Byte Immutability Tests
# ===========================================================================


class TestReportDeterminismAndImmutability:
    def test_report_generation_is_deterministic(self, valid_fixture_path, bs_balance_test_def):
        runner = ScenarioRunner()
        exec_res = runner.run(valid_fixture_path, [bs_balance_test_def])

        generator = ReportGenerator()
        rep1 = generator.generate_report(exec_res, [bs_balance_test_def])
        rep2 = generator.generate_report(exec_res, [bs_balance_test_def])

        assert rep1.to_json() == rep2.to_json()
        assert rep1.metadata.report_id == rep2.metadata.report_id

    def test_source_workbook_sha256_unmodified(self, valid_fixture_path, bs_balance_test_def):
        initial_sha = compute_sha256(valid_fixture_path)

        runner = ScenarioRunner()
        exec_res = runner.run(valid_fixture_path, [bs_balance_test_def])

        generator = ReportGenerator()
        _ = generator.generate_report(exec_res, [bs_balance_test_def])

        final_sha = compute_sha256(valid_fixture_path)
        assert initial_sha == final_sha


# ===========================================================================
# 6. Error Path & Input Validation Tests
# ===========================================================================


class TestReportErrorHandling:
    def test_invalid_execution_result_raises_invalid_input_error(self, bs_balance_test_def):
        generator = ReportGenerator()
        with pytest.raises(InvalidInputError):
            generator.generate_report("invalid_exec_result", [bs_balance_test_def])

    def test_empty_test_definitions_raises_invalid_input_error(self, valid_fixture_path, bs_balance_test_def):
        runner = ScenarioRunner()
        exec_res = runner.run(valid_fixture_path, [bs_balance_test_def])

        generator = ReportGenerator()
        with pytest.raises(InvalidInputError):
            generator.generate_report(exec_res, [])
