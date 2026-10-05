"""
C7 — Security & Error Handling: Focused Security and Error-Handling Tests.

Coverage areas:
  A. Workbook input validation (missing file, directory, bad extension, corrupt file)
  B. Formula/calculation boundaries (calculation failure, missing value, unsupported)
  C. Scenario isolation and temp-resource cleanup
  D. Source workbook integrity (byte-identical after success and failure)
  E. Report serialization / Markdown injection
  F. Status semantic preservation (no false PASS)
  G. Error-message path leakage
"""

import hashlib
import json
import os
import shutil
import struct
import tempfile
import zipfile

import pytest

from finance_model_testbench import (
    AssertionStatus,
    AssertionType,
    CalculationFailedError,
    CellReference,
    InvalidInputError,
    OverallOutcome,
    RecalculationStatus,
    ReportGenerator,
    ScenarioDefinition,
    ScenarioExecutionResult,
    ScenarioInput,
    ScenarioRunner,
    TestDefinition,
    UnsupportedFormatError,
    WorkbookInspectionError,
    WorkbookLoadError,
    absolute_tolerance,
    exact_tolerance,
)
from finance_model_testbench.inspector import WorkbookInspector
from finance_model_testbench.recalculator import WorkbookRecalculator
from finance_model_testbench.report_models import _escape_markdown


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_FIXTURE = os.path.abspath(
    os.path.join("examples", "fixtures", "valid", "valid_three_statement.xlsx")
)
SCENARIO_FIXTURE = os.path.abspath(
    os.path.join("examples", "fixtures", "scenarios", "scenario_three_statement.xlsx")
)


def compute_sha256(path: str) -> str:
    """Return SHA-256 hex digest of a file."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def make_bs_balance_def() -> TestDefinition:
    return TestDefinition(
        test_id="TD_BS_BALANCE",
        description="Balance Sheet: Total Assets == Total Liabilities + Equity",
        assertion_type=AssertionType.EQUALITY,
        operands=[
            CellReference("Balance Sheet", "C5", label="Total Assets"),
            CellReference("Balance Sheet", "C12", label="Total Liabilities & Equity"),
        ],
        tolerance=absolute_tolerance(0.01),
    )


# ===========================================================================
# A. Workbook Input Validation
# ===========================================================================


class TestInputValidation:
    """A — Workbook input validation security tests."""

    def test_missing_file_raises_invalid_input_error(self):
        """Missing file must raise InvalidInputError, not an uncontrolled crash."""
        inspector = WorkbookInspector()
        with pytest.raises(InvalidInputError):
            inspector.inspect("definitely_does_not_exist_abc123.xlsx")

    def test_directory_path_raises_invalid_input_error(self, tmp_path):
        """Supplying a directory instead of a file must raise InvalidInputError."""
        inspector = WorkbookInspector()
        with pytest.raises(InvalidInputError, match="directory"):
            inspector.inspect(str(tmp_path))

    def test_unsupported_extension_raises_error(self, tmp_path):
        """Non-.xlsx extension must raise UnsupportedFormatError."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b,c")
        inspector = WorkbookInspector()
        with pytest.raises(UnsupportedFormatError):
            inspector.inspect(str(csv_file))

    def test_empty_string_path_raises_invalid_input_error(self):
        """Empty string path must raise InvalidInputError."""
        inspector = WorkbookInspector()
        with pytest.raises(InvalidInputError):
            inspector.inspect("")

    def test_non_string_path_raises_invalid_input_error(self):
        """Non-string path must raise InvalidInputError."""
        inspector = WorkbookInspector()
        with pytest.raises(InvalidInputError):
            inspector.inspect(None)  # type: ignore[arg-type]

    def test_corrupt_zip_raises_workbook_load_error(self, tmp_path):
        """A file with .xlsx extension but corrupt ZIP content must raise WorkbookLoadError."""
        corrupt = tmp_path / "corrupt.xlsx"
        corrupt.write_bytes(b"PK\x03\x04NOT_VALID_ZIP_CONTENT_AT_ALL" + b"\x00" * 100)
        inspector = WorkbookInspector()
        with pytest.raises(WorkbookLoadError):
            inspector.inspect(str(corrupt))

    def test_empty_file_raises_workbook_load_error(self, tmp_path):
        """A zero-byte file with .xlsx extension must raise WorkbookLoadError."""
        empty = tmp_path / "empty.xlsx"
        empty.write_bytes(b"")
        inspector = WorkbookInspector()
        with pytest.raises(WorkbookLoadError):
            inspector.inspect(str(empty))

    def test_xls_extension_raises_unsupported_format_error(self, tmp_path):
        """Legacy .xls extension is not supported; must raise UnsupportedFormatError."""
        xls_file = tmp_path / "legacy.xls"
        xls_file.write_bytes(b"\xd0\xcf\x11\xe0" + b"\x00" * 100)  # OLE2 magic
        inspector = WorkbookInspector()
        with pytest.raises(UnsupportedFormatError):
            inspector.inspect(str(xls_file))

    def test_error_message_does_not_expose_full_absolute_path(self, tmp_path):
        """
        Error messages for missing files should expose only the filename,
        not the full absolute path, to limit path leakage in logs/reports.
        """
        nested_dir = tmp_path / "deeply" / "nested" / "dir"
        nested_dir.mkdir(parents=True)
        target = str(nested_dir / "model.xlsx")

        inspector = WorkbookInspector()
        try:
            inspector.inspect(target)
            pytest.fail("Expected InvalidInputError was not raised")
        except InvalidInputError as exc:
            msg = str(exc)
            # The full absolute path should not appear verbatim
            assert str(nested_dir) not in msg, (
                f"Full directory path leaked in error message: {msg}"
            )
            # But the filename should be present
            assert "model.xlsx" in msg

    def test_directory_error_message_does_not_expose_absolute_path(self, tmp_path):
        """Error for directory input should not expose the full absolute path."""
        inspector = WorkbookInspector()
        try:
            inspector.inspect(str(tmp_path))
            pytest.fail("Expected InvalidInputError was not raised")
        except InvalidInputError as exc:
            msg = str(exc)
            # Full absolute path (parent component) should not be exposed verbatim
            parent = str(tmp_path.parent)
            assert parent not in msg, (
                f"Full parent directory leaked in directory error: {msg}"
            )

    def test_recalculator_missing_file_raises_invalid_input_error(self):
        """WorkbookRecalculator must raise InvalidInputError for missing files."""
        recalc = WorkbookRecalculator()
        with pytest.raises(InvalidInputError):
            recalc.recalculate("definitely_does_not_exist_abc123.xlsx")

    def test_scenario_runner_missing_file_raises_invalid_input_error(self):
        """ScenarioRunner must raise InvalidInputError for missing files."""
        runner = ScenarioRunner()
        td = make_bs_balance_def()
        with pytest.raises(InvalidInputError):
            runner.run("nonexistent_workbook.xlsx", [td])

    def test_scenario_runner_empty_test_definitions_raises_error(self):
        """ScenarioRunner must raise InvalidInputError for empty test definitions."""
        runner = ScenarioRunner()
        with pytest.raises(InvalidInputError):
            runner.run(VALID_FIXTURE, [])


# ===========================================================================
# B. Formula Calculation Boundaries
# ===========================================================================


class TestCalculationBoundaries:
    """C — Formula/calculation engine safety."""

    def test_recalculation_of_valid_workbook_succeeds(self):
        """Baseline: recalculating a valid workbook returns SUCCESS status."""
        recalc = WorkbookRecalculator()
        result, status, msg = recalc.recalculate(VALID_FIXTURE)
        assert status == RecalculationStatus.SUCCESS, f"Expected SUCCESS, got {status}: {msg}"

    def test_invalid_scenario_coordinate_raises_scenario_input_error(self):
        """An invalid cell coordinate in scenario inputs must raise ScenarioInputError."""
        from finance_model_testbench.exceptions import ScenarioInputError

        recalc = WorkbookRecalculator()
        bad_input = ScenarioInput(
            cell=CellReference("Assumptions", "INVALID_COORD"),
            value=0.10,
        )
        with pytest.raises(ScenarioInputError, match="Invalid cell coordinate"):
            recalc.recalculate(VALID_FIXTURE, inputs=(bad_input,))

    def test_scenario_input_to_nonexistent_sheet_raises_error(self):
        """A scenario input targeting a sheet that does not exist must raise ScenarioInputError."""
        from finance_model_testbench.exceptions import ScenarioInputError

        runner = ScenarioRunner()
        td = make_bs_balance_def()
        bad_scenario = ScenarioDefinition(
            scenario_id="SCEN_BAD_SHEET",
            description="Targets a non-existent sheet",
            inputs=[
                ScenarioInput(
                    cell=CellReference("DOES_NOT_EXIST", "B2"),
                    value=0.10,
                )
            ],
        )
        with pytest.raises(ScenarioInputError):
            runner.run(VALID_FIXTURE, [td], scenario=bad_scenario)

    def test_missing_cell_returns_incomplete_not_pass(self):
        """A TestDefinition referencing a non-existent cell must produce INCOMPLETE, not PASS."""
        from finance_model_testbench.assertion_engine import AssertionEngine
        from finance_model_testbench.inspector import WorkbookInspector

        inspector = WorkbookInspector()
        inspection = inspector.inspect(VALID_FIXTURE)
        engine = AssertionEngine()

        td = TestDefinition(
            test_id="TD_MISSING_CELL",
            description="Reference to a non-existent cell",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("Balance Sheet", "ZZ9999"),  # definitely does not exist
                CellReference("Balance Sheet", "C5"),
            ],
            tolerance=exact_tolerance(),
        )

        results = engine.run(inspection, [td])
        assert len(results) == 1
        result = results[0]
        assert result.status == AssertionStatus.INCOMPLETE, (
            f"Expected INCOMPLETE for missing cell, got {result.status}"
        )

    def test_recalculation_error_does_not_produce_false_pass(self):
        """
        When recalculation returns ERROR status, the overall report outcome must
        be ERROR, not PASS — even if all assertions individually happened to pass.
        """
        runner = ScenarioRunner()
        td = make_bs_balance_def()
        base_res = runner.run(VALID_FIXTURE, [td])

        # Simulate a recalculation-error execution result
        error_res = ScenarioExecutionResult(
            scenario_id=base_res.scenario_id,
            source_file=base_res.source_file,
            source_sha256=base_res.source_sha256,
            recalculation_status=RecalculationStatus.ERROR,
            recalculation_message="Simulated recalculation engine failure",
            assertion_results=base_res.assertion_results,
            inputs_applied=base_res.inputs_applied,
        )

        generator = ReportGenerator()
        report = generator.generate_report(error_res, [td])
        assert report.summary.overall_outcome == OverallOutcome.ERROR, (
            "ERROR recalculation status must propagate to overall ERROR outcome"
        )
        assert report.summary.overall_outcome != OverallOutcome.PASS

    def test_unsupported_recalculation_does_not_produce_false_pass(self):
        """When recalculation is UNSUPPORTED, overall outcome must not be PASS."""
        runner = ScenarioRunner()
        td = make_bs_balance_def()
        base_res = runner.run(VALID_FIXTURE, [td])

        unsupported_res = ScenarioExecutionResult(
            scenario_id=base_res.scenario_id,
            source_file=base_res.source_file,
            source_sha256=base_res.source_sha256,
            recalculation_status=RecalculationStatus.UNSUPPORTED,
            recalculation_message="Simulated unsupported recalculation",
            assertion_results=base_res.assertion_results,
            inputs_applied=base_res.inputs_applied,
        )

        generator = ReportGenerator()
        report = generator.generate_report(unsupported_res, [td])
        assert report.summary.overall_outcome != OverallOutcome.PASS


# ===========================================================================
# C. Scenario Isolation and Temporary Resource Cleanup
# ===========================================================================


class TestScenarioIsolation:
    """D — Scenario isolation and temp-file cleanup."""

    def test_source_workbook_byte_identical_after_successful_run(self):
        """Source workbook must be byte-identical after a successful scenario run."""
        sha_before = compute_sha256(VALID_FIXTURE)
        runner = ScenarioRunner()
        td = make_bs_balance_def()
        runner.run(VALID_FIXTURE, [td])
        sha_after = compute_sha256(VALID_FIXTURE)
        assert sha_before == sha_after, "Source workbook was mutated by scenario runner!"

    def test_source_workbook_byte_identical_after_scenario_with_inputs(self):
        """Source workbook must be byte-identical after a scenario with assumption changes."""
        sha_before = compute_sha256(SCENARIO_FIXTURE)
        runner = ScenarioRunner()
        td = make_bs_balance_def()
        scenario = ScenarioDefinition(
            scenario_id="SCEN_INTEGRITY_CHECK",
            description="Verify source integrity after applying scenario inputs",
            inputs=[ScenarioInput(cell=CellReference("Assumptions", "B2"), value=0.15)],
        )
        runner.run(SCENARIO_FIXTURE, [td], scenario=scenario)
        sha_after = compute_sha256(SCENARIO_FIXTURE)
        assert sha_before == sha_after, "Source workbook was mutated by scenario with inputs!"

    def test_no_temp_directory_leaks_after_successful_run(self, tmp_path, monkeypatch):
        """
        Temporary directories created during recalculation must be cleaned up
        after a successful run.
        """
        created_dirs = []
        original_mkdtemp = tempfile.mkdtemp

        def tracked_mkdtemp(**kwargs):
            d = original_mkdtemp(**kwargs)
            created_dirs.append(d)
            return d

        monkeypatch.setattr(tempfile, "mkdtemp", tracked_mkdtemp)

        recalc = WorkbookRecalculator()
        recalc.recalculate(VALID_FIXTURE)

        for d in created_dirs:
            assert not os.path.exists(d), (
                f"Temporary directory '{d}' was not cleaned up after successful recalculation"
            )

    def test_no_temp_directory_leaks_after_failed_run(self, monkeypatch):
        """
        Temporary directories must be cleaned up even when recalculation fails
        due to a corrupt workbook.
        """
        created_dirs = []
        original_mkdtemp = tempfile.mkdtemp

        def tracked_mkdtemp(**kwargs):
            d = original_mkdtemp(**kwargs)
            created_dirs.append(d)
            return d

        monkeypatch.setattr(tempfile, "mkdtemp", tracked_mkdtemp)

        # Use a corrupt file to force a failure path through recalculation
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tf:
            corrupt_path = tf.name
            tf.write(b"PK\x03\x04NOT_VALID_ZIP\x00" * 20)

        try:
            recalc = WorkbookRecalculator()
            # This will raise WorkbookLoadError before temp dir is created, or
            # return UNSUPPORTED after creating temp dir. Either way, no temp leak.
            try:
                recalc.recalculate(corrupt_path)
            except Exception:
                pass  # Expected; we only care about cleanup

            for d in created_dirs:
                assert not os.path.exists(d), (
                    f"Temporary directory '{d}' was not cleaned up after failed recalculation"
                )
        finally:
            os.unlink(corrupt_path)

    def test_repeated_scenarios_do_not_share_mutable_state(self):
        """
        Running two independent scenarios sequentially must produce isolated results.
        The second scenario must not be affected by the first scenario's inputs.
        """
        runner = ScenarioRunner()
        td = make_bs_balance_def()

        scenario_a = ScenarioDefinition(
            scenario_id="SCEN_ISOLATION_A",
            description="First scenario: 10% revenue growth",
            inputs=[ScenarioInput(cell=CellReference("Assumptions", "B2"), value=0.10)],
        )
        scenario_b = ScenarioDefinition(
            scenario_id="SCEN_ISOLATION_B",
            description="Second scenario: 20% revenue growth",
            inputs=[ScenarioInput(cell=CellReference("Assumptions", "B2"), value=0.20)],
        )

        results = runner.run_scenarios(SCENARIO_FIXTURE, [td], [scenario_a, scenario_b])
        assert len(results) == 2
        # Both should succeed (isolation check: no state leakage)
        assert results[0].recalculation_status == RecalculationStatus.SUCCESS
        assert results[1].recalculation_status == RecalculationStatus.SUCCESS
        # SHA-256 of source must be identical in both results
        assert results[0].source_sha256 == results[1].source_sha256


# ===========================================================================
# D. Source Workbook Integrity
# ===========================================================================


class TestSourceIntegrity:
    """E — File integrity checks."""

    def test_sha256_computed_on_original_file_before_run(self):
        """SHA-256 recorded in ScenarioExecutionResult must match the actual source file."""
        actual_sha = compute_sha256(VALID_FIXTURE)
        runner = ScenarioRunner()
        td = make_bs_balance_def()
        result = runner.run(VALID_FIXTURE, [td])
        assert result.source_sha256 == actual_sha, (
            "Recorded SHA-256 does not match actual source file hash"
        )

    def test_report_source_sha256_matches_execution_result(self):
        """SHA-256 in the report metadata must match the execution result's SHA-256."""
        runner = ScenarioRunner()
        td = make_bs_balance_def()
        exec_result = runner.run(VALID_FIXTURE, [td])

        generator = ReportGenerator()
        report = generator.generate_report(exec_result, [td])

        assert report.metadata.source_sha256 == exec_result.source_sha256

    def test_report_exposes_filename_not_absolute_path(self):
        """Report metadata must expose only the filename, not the full absolute path."""
        runner = ScenarioRunner()
        td = make_bs_balance_def()
        exec_result = runner.run(VALID_FIXTURE, [td])

        generator = ReportGenerator()
        report = generator.generate_report(exec_result, [td])

        # source_filename must be just the basename
        assert report.metadata.source_filename == "valid_three_statement.xlsx"
        # It must not contain path separators
        assert os.sep not in report.metadata.source_filename
        assert "/" not in report.metadata.source_filename

    def test_json_report_does_not_expose_absolute_path(self):
        """JSON report must not include the full absolute path of the source workbook."""
        runner = ScenarioRunner()
        td = make_bs_balance_def()
        exec_result = runner.run(VALID_FIXTURE, [td])

        generator = ReportGenerator()
        report = generator.generate_report(exec_result, [td])
        json_str = report.to_json()

        # The absolute fixture path (directory component) must not appear in JSON output
        fixture_dir = os.path.dirname(VALID_FIXTURE)
        assert fixture_dir not in json_str, (
            "JSON report exposes absolute source file directory path"
        )


# ===========================================================================
# E. Markdown Injection and Report Serialization
# ===========================================================================


class TestMarkdownInjection:
    """F — Report Markdown injection and serialization security."""

    def test_escape_markdown_backtick_injection(self):
        """Backtick injection must be neutralised."""
        result = _escape_markdown("value with `code block` injection")
        assert "`" not in result
        assert "'" in result

    def test_escape_markdown_pipe_injection(self):
        """Pipe characters must be escaped to prevent table-row injection."""
        result = _escape_markdown("value | with | pipes")
        # Escaped form is \| which still contains | but not as a bare structural pipe
        assert "\\|" in result
        # The original unescaped bare pipe preceded/followed by spaces must not survive
        assert " | " not in result

    def test_escape_markdown_newline_injection(self):
        """Newline characters must be collapsed to prevent heading/block injection."""
        result = _escape_markdown("line one\nline two")
        assert "\n" not in result
        result2 = _escape_markdown("line one\r\nline two")
        assert "\n" not in result2
        assert "\r" not in result2

    def test_escape_markdown_hash_injection(self):
        """Hash characters must be escaped to prevent heading-level injection."""
        result = _escape_markdown("# Injected Heading")
        # Must be converted to HTML entity &#35;
        assert "&#35;" in result
        # Must not start with # (which would be a Markdown heading)
        assert not result.startswith("#")

    def test_escape_markdown_asterisk_injection(self):
        """Asterisk characters must be escaped to prevent bold/italic injection."""
        result = _escape_markdown("**bold injection**")
        assert "**" not in result
        assert "&#42;" in result

    def test_escape_markdown_underscore_injection(self):
        """Underscore characters must be escaped to prevent italic injection."""
        result = _escape_markdown("_italic injection_")
        assert "_" not in result
        assert "&#95;" in result

    def test_escape_markdown_combined_injection_string(self):
        """Combined injection attempt must be fully neutralised."""
        malicious = "# Heading\n## SubHeading\n| col1 | col2 |\n|------|------|\n`code` **bold** _italic_"
        result = _escape_markdown(malicious)
        # Hash converted to HTML entity — no leading # as heading
        assert not result.startswith("#"), "Result must not start with a heading marker"
        assert "&#35;" in result
        # Newlines collapsed to spaces
        assert "\n" not in result
        # Backticks replaced
        assert "`" not in result
        # Bold markers broken up (each * replaced with &#42;)
        assert "**" not in result
        # Underscore replaced
        assert "_" not in result

    def test_empty_string_escape_returns_empty(self):
        """Empty input must return empty string, not raise or return None."""
        assert _escape_markdown("") == ""
        assert _escape_markdown(None) == ""  # type: ignore[arg-type]

    def test_markdown_report_with_injected_description_is_safe(self):
        """
        A TestDefinition with injected Markdown in its description must not
        produce structural injection in the rendered Markdown report.
        """
        malicious_td = TestDefinition(
            test_id="TD_INJECT",
            description="# Injected Heading\n| fake | table |\n**bold** _italic_",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("Balance Sheet", "C5"),
                CellReference("Balance Sheet", "C12"),
            ],
            tolerance=absolute_tolerance(0.01),
        )

        runner = ScenarioRunner()
        exec_result = runner.run(VALID_FIXTURE, [malicious_td])

        generator = ReportGenerator()
        report = generator.generate_report(exec_result, [malicious_td])
        md = report.to_markdown()

        # Must not contain raw injected heading within evidence section
        assert "# Injected Heading" not in md
        assert "## SubHeading" not in md
        # Must not contain raw unescaped pipe sequences (table rows)
        # Legitimate table rows from report structure are fine; check for injected fake table
        assert "| fake | table |" not in md

    def test_json_serialization_with_none_values(self):
        """
        JSON serialization must handle None for expected/observed/difference without
        converting them to empty strings, zero, or fabricated values.
        """
        runner = ScenarioRunner()
        td = TestDefinition(
            test_id="TD_MISSING",
            description="Reference to missing cell for JSON null check",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("Balance Sheet", "ZZ9999"),  # does not exist
                CellReference("Balance Sheet", "C5"),
            ],
            tolerance=exact_tolerance(),
        )
        exec_result = runner.run(VALID_FIXTURE, [td])

        generator = ReportGenerator()
        report = generator.generate_report(exec_result, [td])
        json_str = report.to_json()
        data = json.loads(json_str)

        ev = data["evidence"][0]
        assert ev["status"] == "INCOMPLETE"
        # expected/observed/difference must be null (None → JSON null), not 0 or ""
        assert ev["expected"] is None
        assert ev["observed"] is None

    def test_json_uses_standard_library_serialization(self):
        """JSON output must be valid, parseable JSON (standard library safety check)."""
        runner = ScenarioRunner()
        td = make_bs_balance_def()
        exec_result = runner.run(VALID_FIXTURE, [td])

        generator = ReportGenerator()
        report = generator.generate_report(exec_result, [td])
        json_str = report.to_json()

        # Must be parseable by standard json module
        data = json.loads(json_str)
        assert isinstance(data, dict)
        assert "metadata" in data
        assert "summary" in data
        assert "evidence" in data


# ===========================================================================
# F. Status Semantic Preservation (No False PASS)
# ===========================================================================


class TestStatusSemantics:
    """F — Status semantic preservation: no failed/incomplete operation becomes PASS."""

    def test_five_distinct_statuses_are_defined(self):
        """All five documented statuses must remain distinct enum members."""
        from finance_model_testbench.assertion_models import AssertionStatus
        values = {s.value for s in AssertionStatus}
        assert "PASS" in values
        assert "FAIL" in values
        assert "ERROR" in values
        assert "UNSUPPORTED" in values
        assert "INCOMPLETE" in values
        assert len(values) == 5

    def test_five_overall_outcomes_are_defined(self):
        """All five overall outcome statuses must remain distinct enum members."""
        values = {s.value for s in OverallOutcome}
        assert "PASS" in values
        assert "FAIL" in values
        assert "ERROR" in values
        assert "UNSUPPORTED" in values
        assert "INCOMPLETE" in values
        assert len(values) == 5

    def test_incomplete_is_not_equal_to_fail(self):
        """INCOMPLETE must remain semantically distinct from FAIL."""
        assert AssertionStatus.INCOMPLETE != AssertionStatus.FAIL
        assert AssertionStatus.INCOMPLETE.value != AssertionStatus.FAIL.value

    def test_error_outcome_takes_precedence_over_fail(self):
        """Overall ERROR must take precedence over FAIL in mixed-status report."""
        runner = ScenarioRunner()
        td = make_bs_balance_def()
        base_res = runner.run(VALID_FIXTURE, [td])

        # Force an execution result that has both FAIL assertions and ERROR recalculation
        from finance_model_testbench.assertion_models import AssertionResult
        fail_result = AssertionResult(
            test_id="TD_FORCED_FAIL",
            status=AssertionStatus.FAIL,
            assertion_type=AssertionType.EQUALITY,
            tolerance=absolute_tolerance(0.01),
            resolved=[],
            message="FAIL: forced for test",
        )
        mixed_res = ScenarioExecutionResult(
            scenario_id="SCEN_MIXED",
            source_file=base_res.source_file,
            source_sha256=base_res.source_sha256,
            recalculation_status=RecalculationStatus.ERROR,
            recalculation_message="Forced error",
            assertion_results=(fail_result,),
            inputs_applied={},
        )

        td_fail = TestDefinition(
            test_id="TD_FORCED_FAIL",
            description="Forced FAIL test",
            assertion_type=AssertionType.EQUALITY,
            operands=[CellReference("Balance Sheet", "C5"), CellReference("Balance Sheet", "C12")],
            tolerance=absolute_tolerance(0.01),
        )

        generator = ReportGenerator()
        report = generator.generate_report(mixed_res, [td_fail])
        assert report.summary.overall_outcome == OverallOutcome.ERROR

    def test_mixed_pass_and_incomplete_outcome_is_not_pass(self):
        """A report with PASS and INCOMPLETE assertions must not produce overall PASS."""
        runner = ScenarioRunner()

        # One passing assertion
        td_pass = make_bs_balance_def()
        # One INCOMPLETE assertion (missing cell)
        td_incomplete = TestDefinition(
            test_id="TD_INCOMPLETE",
            description="Forces INCOMPLETE via missing cell",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("Balance Sheet", "ZZ9999"),
                CellReference("Balance Sheet", "C5"),
            ],
            tolerance=exact_tolerance(),
        )

        exec_result = runner.run(VALID_FIXTURE, [td_pass, td_incomplete])
        generator = ReportGenerator()
        report = generator.generate_report(exec_result, [td_pass, td_incomplete])

        assert report.summary.overall_outcome != OverallOutcome.PASS
        assert report.summary.incomplete_count >= 1
        assert report.summary.pass_count >= 1

    def test_corrupt_workbook_does_not_produce_pass(self, tmp_path):
        """A corrupt workbook must never produce a PASS result — it must raise or ERROR."""
        corrupt = tmp_path / "corrupt.xlsx"
        corrupt.write_bytes(b"PK\x03\x04NOT_VALID_ZIP" + b"\x00" * 100)

        runner = ScenarioRunner()
        td = make_bs_balance_def()

        with pytest.raises(Exception) as exc_info:
            runner.run(str(corrupt), [td])

        # The exception must not be a false success; any real error exception is acceptable
        exc_type = type(exc_info.value).__name__
        assert exc_type not in ("AssertionError",), (
            f"Unexpected AssertionError (possible false PASS confusion): {exc_info.value}"
        )
