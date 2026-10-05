"""
Comprehensive C5 Test Suite — Scenario Execution and Formula Recalculation.
"""

import hashlib
import os
import pytest

from finance_model_testbench import (
    AssertionEngine,
    AssertionResult,
    AssertionStatus,
    AssertionType,
    CellReference,
    InvalidInputError,
    RecalculationStatus,
    ScenarioDefinition,
    ScenarioExecutionResult,
    ScenarioInput,
    ScenarioInputError,
    ScenarioRunner,
    TestDefinition,
    WorkbookInspector,
    WorkbookRecalculator,
    absolute_tolerance,
    exact_tolerance,
)


@pytest.fixture
def valid_fixture_path():
    return os.path.abspath(os.path.join("examples", "fixtures", "valid", "valid_three_statement.xlsx"))


@pytest.fixture
def bs_defective_path():
    return os.path.abspath(os.path.join("examples", "fixtures", "defective", "defective_balance_sheet_imbalance.xlsx"))


@pytest.fixture
def re_defective_path():
    return os.path.abspath(os.path.join("examples", "fixtures", "defective", "defective_retained_earnings_rollforward.xlsx"))


@pytest.fixture
def cf_defective_path():
    return os.path.abspath(os.path.join("examples", "fixtures", "defective", "defective_cash_flow_linkage.xlsx"))


@pytest.fixture
def scenario_fixture_path():
    return os.path.abspath(os.path.join("examples", "fixtures", "scenarios", "scenario_three_statement.xlsx"))


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
        expected_value=112.5,  # Net Income from Income Statement
        tolerance=absolute_tolerance(0.01),
    )


@pytest.fixture
def cf_linkage_test_def():
    return TestDefinition(
        test_id="TD_CF_LINK",
        description="Cash Flow Depreciation linkage: CF Depreciation == IS Depreciation",
        assertion_type=AssertionType.EQUALITY,
        operands=[
            CellReference("Cash Flow Statement", "B3", label="CF Depreciation"),
            CellReference("Income Statement", "C5", label="IS Depreciation"),
        ],
        tolerance=absolute_tolerance(0.01),
    )


def compute_file_sha256(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


# ===========================================================================
# 1. Recalculation Engine Tests
# ===========================================================================


class TestWorkbookRecalculator:
    def test_recalculate_valid_fixture(self, valid_fixture_path):
        recalculator = WorkbookRecalculator()
        result, status, msg = recalculator.recalculate(valid_fixture_path)

        assert status == RecalculationStatus.SUCCESS
        assert "completed successfully" in msg
        assert len(result.worksheets) == 4

        # Check recalculated cell values
        is_sheet = result.worksheets["Income Statement"]
        assert is_sheet.cells["C2"].cached_value == 1050.0  # Revenue
        assert is_sheet.cells["C10"].cached_value == 112.5  # Net Income

        bs_sheet = result.worksheets["Balance Sheet"]
        assert bs_sheet.cells["C5"].cached_value == 1012.5  # Total Assets
        assert bs_sheet.cells["C12"].cached_value == 1012.5  # Total L+E

    def test_recalculate_nonexistent_file(self):
        recalculator = WorkbookRecalculator()
        with pytest.raises(InvalidInputError):
            recalculator.recalculate("nonexistent_path_xyz.xlsx")


# ===========================================================================
# 2. Baseline Assertion Rerun & Defect Detection Tests
# ===========================================================================


class TestBaselineAssertionRecalculation:
    def test_valid_fixture_passes_after_recalculation(
        self, valid_fixture_path, bs_balance_test_def, re_rollforward_test_def, cf_linkage_test_def
    ):
        runner = ScenarioRunner()
        res = runner.run(valid_fixture_path, [bs_balance_test_def, re_rollforward_test_def, cf_linkage_test_def])

        assert res.recalculation_status == RecalculationStatus.SUCCESS
        assert len(res.assertion_results) == 3

        # All 3 assertions must PASS when formula values are recalculated
        for a_res in res.assertion_results:
            assert a_res.status == AssertionStatus.PASS

    def test_detects_balance_sheet_imbalance_after_recalculation(self, bs_defective_path, bs_balance_test_def):
        runner = ScenarioRunner()
        res = runner.run(bs_defective_path, [bs_balance_test_def])

        assert res.recalculation_status == RecalculationStatus.SUCCESS
        assert len(res.assertion_results) == 1
        a_res = res.assertion_results[0]

        # Assets = 1062.5, L+E = 1012.5 -> FAIL
        assert a_res.status == AssertionStatus.FAIL
        assert a_res.observed == 1062.5
        assert a_res.expected == 1012.5

    def test_detects_retained_earnings_defect_after_recalculation(self, re_defective_path, re_rollforward_test_def):
        runner = ScenarioRunner()
        res = runner.run(re_defective_path, [re_rollforward_test_def])

        assert res.recalculation_status == RecalculationStatus.SUCCESS
        assert len(res.assertion_results) == 1
        a_res = res.assertion_results[0]

        # Ending RE - Beg RE = 312.5 - 300 = 12.5 ≠ expected Net Income 112.5 -> FAIL
        assert a_res.status == AssertionStatus.FAIL
        assert a_res.observed == 12.5
        assert a_res.expected == 112.5

    def test_detects_cash_flow_linkage_defect_after_recalculation(self, cf_defective_path, cf_linkage_test_def):
        runner = ScenarioRunner()
        res = runner.run(cf_defective_path, [cf_linkage_test_def])

        assert res.recalculation_status == RecalculationStatus.SUCCESS
        assert len(res.assertion_results) == 1
        a_res = res.assertion_results[0]

        # CF Depr = 0.0 ≠ IS Depr = 50.0 -> FAIL
        assert a_res.status == AssertionStatus.FAIL
        assert a_res.observed == 0.0
        assert a_res.expected == 50.0


# ===========================================================================
# 3. Controlled Scenario Input Execution Tests
# ===========================================================================


class TestScenarioInputExecution:
    def test_scenario_revenue_growth_increase(self, scenario_fixture_path, bs_balance_test_def):
        runner = ScenarioRunner()
        scenario = ScenarioDefinition(
            scenario_id="SCEN_REV_GROWTH_10",
            description="Test 10% Revenue Growth Rate scenario",
            inputs=[
                ScenarioInput(
                    cell=CellReference("Assumptions", "B2"),
                    value=0.10,
                    label="Revenue Growth Rate",
                )
            ],
        )

        res = runner.run(scenario_fixture_path, [bs_balance_test_def], scenario=scenario)

        assert res.scenario_id == "SCEN_REV_GROWTH_10"
        assert res.recalculation_status == RecalculationStatus.SUCCESS
        assert len(res.assertion_results) == 1
        assert res.assertion_results[0].status == AssertionStatus.PASS
        assert res.assertion_results[0].observed == 1020.0
        assert res.assertion_results[0].expected == 1020.0

    def test_scenario_multiple_inputs(self, scenario_fixture_path, bs_balance_test_def):
        runner = ScenarioRunner()
        scenario = ScenarioDefinition(
            scenario_id="SCEN_STRESS_TEST",
            description="Stress test with 15% revenue growth and 25% operating margin",
            inputs=[
                ScenarioInput(cell=CellReference("Assumptions", "B2"), value=0.15),
                ScenarioInput(cell=CellReference("Assumptions", "B3"), value=0.25),
            ],
        )

        res = runner.run(scenario_fixture_path, [bs_balance_test_def], scenario=scenario)

        assert res.recalculation_status == RecalculationStatus.SUCCESS
        assert res.assertion_results[0].status == AssertionStatus.PASS
        # Verify balance sheet remains balanced under multi-input change
        assert res.assertion_results[0].observed == res.assertion_results[0].expected


# ===========================================================================
# 4. Scenario Isolation & Determinism Tests
# ===========================================================================


class TestScenarioIsolationAndDeterminism:
    def test_scenarios_do_not_contaminate_each_other(self, scenario_fixture_path, bs_balance_test_def):
        runner = ScenarioRunner()
        scen_a = ScenarioDefinition(
            scenario_id="SCEN_A",
            description="10% Rev Growth",
            inputs=[ScenarioInput(cell=CellReference("Assumptions", "B2"), value=0.10)],
        )
        scen_b = ScenarioDefinition(
            scenario_id="SCEN_B",
            description="20% Rev Growth",
            inputs=[ScenarioInput(cell=CellReference("Assumptions", "B2"), value=0.20)],
        )

        results = runner.run_scenarios(scenario_fixture_path, [bs_balance_test_def], [scen_a, scen_b])

        assert len(results) == 2
        res_a, res_b = results[0], results[1]

        assert res_a.scenario_id == "SCEN_A"
        assert res_b.scenario_id == "SCEN_B"

        # Scenario A Assets = 1020.0, Scenario B Assets = 1035.0
        assert res_a.assertion_results[0].observed == 1020.0
        assert res_b.assertion_results[0].observed == 1035.0

    def test_repeated_scenario_execution_is_deterministic(self, scenario_fixture_path, bs_balance_test_def):
        runner = ScenarioRunner()
        scenario = ScenarioDefinition(
            scenario_id="SCEN_REPEAT",
            description="Deterministic repetition test",
            inputs=[ScenarioInput(cell=CellReference("Assumptions", "B2"), value=0.10)],
        )

        res1 = runner.run(scenario_fixture_path, [bs_balance_test_def], scenario=scenario)
        res2 = runner.run(scenario_fixture_path, [bs_balance_test_def], scenario=scenario)

        assert res1.to_dict() == res2.to_dict()

    def test_source_workbook_sha256_immutable(self, valid_fixture_path, bs_balance_test_def):
        initial_sha = compute_file_sha256(valid_fixture_path)

        runner = ScenarioRunner()
        scenario = ScenarioDefinition(
            scenario_id="SCEN_IMMUTABLE",
            description="Source byte immutability check",
            inputs=[ScenarioInput(cell=CellReference("Assumptions", "B2"), value=0.10)],
        )
        res = runner.run(valid_fixture_path, [bs_balance_test_def], scenario=scenario)

        final_sha = compute_file_sha256(valid_fixture_path)
        assert initial_sha == final_sha
        assert res.source_sha256 == initial_sha


# ===========================================================================
# 5. Error Path & Input Validation Tests
# ===========================================================================


class TestScenarioErrorHandling:
    def test_invalid_target_sheet_raises_scenario_input_error(self, valid_fixture_path, bs_balance_test_def):
        runner = ScenarioRunner()
        scenario = ScenarioDefinition(
            scenario_id="SCEN_BAD_SHEET",
            description="Non-existent sheet target",
            inputs=[ScenarioInput(cell=CellReference("NonExistentSheet", "B2"), value=0.10)],
        )
        with pytest.raises(ScenarioInputError):
            runner.run(valid_fixture_path, [bs_balance_test_def], scenario=scenario)

    def test_invalid_cell_coordinate_raises_scenario_input_error(self, valid_fixture_path, bs_balance_test_def):
        runner = ScenarioRunner()
        scenario = ScenarioDefinition(
            scenario_id="SCEN_BAD_COORD",
            description="Invalid coordinate format",
            inputs=[ScenarioInput(cell=CellReference("Assumptions", "INVALID_COORD"), value=0.10)],
        )
        with pytest.raises(ScenarioInputError):
            runner.run(valid_fixture_path, [bs_balance_test_def], scenario=scenario)

    def test_empty_test_definitions_raises_invalid_input_error(self, valid_fixture_path):
        runner = ScenarioRunner()
        with pytest.raises(InvalidInputError):
            runner.run(valid_fixture_path, [])
