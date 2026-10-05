"""
Tests for C4 — Deterministic Test Engine.

Test coverage:
1. TestDefinition / ToleranceSpec model validation
2. Value resolution (numeric, missing, non-numeric, formula cached, formula no cache)
3. EQUALITY assertions (PASS, FAIL, edge cases)
4. DIFFERENCE assertions (PASS, FAIL, zero, negatives)
5. SUM_EQUALITY assertions (PASS, FAIL)
6. Status semantics (PASS / FAIL / ERROR / INCOMPLETE / UNSUPPORTED)
7. Tolerance model (EXACT, ABSOLUTE, RELATIVE, edge cases)
8. Financial fixture assertions against valid and defective workbooks
9. Determinism (repeated runs produce identical results)
10. No filename-based defect detection (engine evaluates relationships only)
11. No source workbook mutation during assertion evaluation
12. C4 engine returns structured results under all conditions
"""

import hashlib
import os
from typing import List

import pytest

from finance_model_testbench.assertion_engine import AssertionEngine, _resolve_reference, _satisfies_tolerance
from finance_model_testbench.assertion_models import (
    AssertionResult,
    AssertionStatus,
    AssertionType,
    CellReference,
    ResolvedValue,
    ResolvedValueKind,
    TestDefinition,
    ToleranceSpec,
    ToleranceType,
    absolute_tolerance,
    exact_tolerance,
    relative_tolerance,
)
from finance_model_testbench.exceptions import (
    InvalidTestDefinitionError,
)
from finance_model_testbench.inspector import WorkbookInspector
from finance_model_testbench.models import WorkbookInspectionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_fixture_path(relative_subpath: str) -> str:
    return os.path.join("examples", "fixtures", relative_subpath)


def compute_file_hash(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()


def inspect_fixture(relative_subpath: str) -> WorkbookInspectionResult:
    return WorkbookInspector().inspect(get_fixture_path(relative_subpath))


# ---------------------------------------------------------------------------
# 1. ToleranceSpec model validation
# ---------------------------------------------------------------------------


class TestToleranceSpec:
    def test_exact_tolerance_factory(self):
        spec = exact_tolerance()
        assert spec.tolerance_type == ToleranceType.EXACT
        assert spec.tolerance_value == 0.0

    def test_absolute_tolerance_factory(self):
        spec = absolute_tolerance(0.01)
        assert spec.tolerance_type == ToleranceType.ABSOLUTE
        assert spec.tolerance_value == 0.01

    def test_relative_tolerance_factory(self):
        spec = relative_tolerance(0.001, min_reference=0.01)
        assert spec.tolerance_type == ToleranceType.RELATIVE
        assert spec.tolerance_value == 0.001
        assert spec.min_reference == 0.01

    def test_negative_tolerance_value_rejected(self):
        with pytest.raises(ValueError, match="tolerance_value"):
            ToleranceSpec(tolerance_type=ToleranceType.ABSOLUTE, tolerance_value=-0.01)

    def test_zero_min_reference_rejected(self):
        with pytest.raises(ValueError, match="min_reference"):
            ToleranceSpec(
                tolerance_type=ToleranceType.RELATIVE,
                tolerance_value=0.001,
                min_reference=0.0,
            )

    def test_negative_min_reference_rejected(self):
        with pytest.raises(ValueError, match="min_reference"):
            ToleranceSpec(
                tolerance_type=ToleranceType.RELATIVE,
                tolerance_value=0.001,
                min_reference=-1.0,
            )

    def test_to_dict(self):
        spec = absolute_tolerance(5.0)
        d = spec.to_dict()
        assert d["tolerance_type"] == "ABSOLUTE"
        assert d["tolerance_value"] == 5.0


# ---------------------------------------------------------------------------
# 2. TestDefinition model validation
# ---------------------------------------------------------------------------


class TestTestDefinition:
    def _make_refs(self, n: int) -> List[CellReference]:
        return [CellReference(sheet_name="Sheet1", coordinate=f"A{i+1}") for i in range(n)]

    def test_valid_equality_definition(self):
        td = TestDefinition(
            test_id="TD_001",
            description="Test equality",
            assertion_type=AssertionType.EQUALITY,
            operands=self._make_refs(2),
            tolerance=exact_tolerance(),
        )
        assert td.test_id == "TD_001"

    def test_equality_requires_exactly_two_operands(self):
        with pytest.raises(ValueError, match="exactly 2 operands"):
            TestDefinition(
                test_id="TD_001",
                description="Test",
                assertion_type=AssertionType.EQUALITY,
                operands=self._make_refs(3),
                tolerance=exact_tolerance(),
            )

    def test_difference_requires_exactly_two_operands(self):
        with pytest.raises(ValueError, match="exactly 2 operands"):
            TestDefinition(
                test_id="TD_001",
                description="Test",
                assertion_type=AssertionType.DIFFERENCE,
                operands=self._make_refs(3),
                tolerance=exact_tolerance(),
                expected_value=0.0,
            )

    def test_sum_equality_requires_at_least_two_operands(self):
        with pytest.raises(ValueError, match="at least 2 operands"):
            TestDefinition(
                test_id="TD_001",
                description="Test",
                assertion_type=AssertionType.SUM_EQUALITY,
                operands=self._make_refs(1),
                tolerance=exact_tolerance(),
                expected_value=0.0,
            )

    def test_empty_test_id_rejected(self):
        with pytest.raises(ValueError, match="test_id"):
            TestDefinition(
                test_id="",
                description="Test",
                assertion_type=AssertionType.EQUALITY,
                operands=self._make_refs(2),
                tolerance=exact_tolerance(),
            )

    def test_empty_description_rejected(self):
        with pytest.raises(ValueError, match="description"):
            TestDefinition(
                test_id="TD_001",
                description="",
                assertion_type=AssertionType.EQUALITY,
                operands=self._make_refs(2),
                tolerance=exact_tolerance(),
            )

    def test_no_operands_rejected(self):
        with pytest.raises(ValueError, match="operands"):
            TestDefinition(
                test_id="TD_001",
                description="Test",
                assertion_type=AssertionType.EQUALITY,
                operands=[],
                tolerance=exact_tolerance(),
            )

    def test_to_dict(self):
        refs = self._make_refs(2)
        td = TestDefinition(
            test_id="TD_001",
            description="Test equality",
            assertion_type=AssertionType.EQUALITY,
            operands=refs,
            tolerance=absolute_tolerance(0.5),
        )
        d = td.to_dict()
        assert d["test_id"] == "TD_001"
        assert d["assertion_type"] == "EQUALITY"
        assert len(d["operands"]) == 2


# ---------------------------------------------------------------------------
# 3. Value resolution (_resolve_reference)
# ---------------------------------------------------------------------------


class TestValueResolution:
    def setup_method(self):
        self.inspection = inspect_fixture("valid/valid_three_statement.xlsx")

    def test_numeric_cell_resolves_as_numeric(self):
        # Assumptions!B2 = 0.05 (a plain numeric cell)
        ref = CellReference(sheet_name="Assumptions", coordinate="B2")
        resolved = _resolve_reference(ref, self.inspection)
        assert resolved.kind == ResolvedValueKind.NUMERIC
        assert resolved.is_usable
        assert resolved.numeric == pytest.approx(0.05, abs=1e-9)

    def test_formula_cell_with_cached_value(self):
        # Income Statement C2 = "=B2*(1+Assumptions!B2)" — formula with cached value
        ref = CellReference(sheet_name="Income Statement", coordinate="C2")
        resolved = _resolve_reference(ref, self.inspection)
        # openpyxl saves cached value from last Excel calculation;
        # fixtures were saved by openpyxl which does not calculate, so cached_value is None
        # → FORMULA_NO_CACHE or FORMULA_CACHED depending on actual fixture state
        assert resolved.kind in (
            ResolvedValueKind.FORMULA_CACHED,
            ResolvedValueKind.FORMULA_NO_CACHE,
        )

    def test_missing_sheet_returns_missing(self):
        ref = CellReference(sheet_name="NonExistentSheet", coordinate="A1")
        resolved = _resolve_reference(ref, self.inspection)
        assert resolved.kind == ResolvedValueKind.MISSING
        assert not resolved.is_usable
        assert resolved.numeric is None

    def test_missing_cell_returns_missing(self):
        ref = CellReference(sheet_name="Assumptions", coordinate="Z99")
        resolved = _resolve_reference(ref, self.inspection)
        assert resolved.kind == ResolvedValueKind.MISSING
        assert not resolved.is_usable

    def test_missing_cell_not_treated_as_zero(self):
        """Blank/missing cells must never be silently coerced to 0."""
        ref = CellReference(sheet_name="Assumptions", coordinate="Z99")
        resolved = _resolve_reference(ref, self.inspection)
        assert resolved.numeric is None

    def test_non_numeric_cell_returns_non_numeric(self):
        # Assumptions!A2 = "Revenue Growth Rate" (a string label)
        ref = CellReference(sheet_name="Assumptions", coordinate="A2")
        resolved = _resolve_reference(ref, self.inspection)
        assert resolved.kind == ResolvedValueKind.NON_NUMERIC
        assert not resolved.is_usable
        assert resolved.numeric is None


# ---------------------------------------------------------------------------
# 4. Tolerance evaluator (_satisfies_tolerance)
# ---------------------------------------------------------------------------


class TestToleranceEvaluator:
    def test_exact_equal(self):
        assert _satisfies_tolerance(100.0, 100.0, exact_tolerance()) is True

    def test_exact_not_equal(self):
        assert _satisfies_tolerance(100.0001, 100.0, exact_tolerance()) is False

    def test_absolute_within_tolerance(self):
        spec = absolute_tolerance(0.01)
        assert _satisfies_tolerance(100.005, 100.0, spec) is True

    def test_absolute_outside_tolerance(self):
        spec = absolute_tolerance(0.01)
        assert _satisfies_tolerance(100.02, 100.0, spec) is False

    def test_absolute_exactly_at_tolerance(self):
        spec = absolute_tolerance(5.0)
        assert _satisfies_tolerance(105.0, 100.0, spec) is True
        assert _satisfies_tolerance(105.01, 100.0, spec) is False

    def test_absolute_negative_values(self):
        spec = absolute_tolerance(1.0)
        assert _satisfies_tolerance(-100.5, -100.0, spec) is True
        assert _satisfies_tolerance(-101.5, -100.0, spec) is False

    def test_absolute_zero_expected(self):
        spec = absolute_tolerance(0.01)
        assert _satisfies_tolerance(0.005, 0.0, spec) is True
        assert _satisfies_tolerance(0.02, 0.0, spec) is False

    def test_relative_within_tolerance(self):
        spec = relative_tolerance(0.01)  # 1%
        assert _satisfies_tolerance(100.5, 100.0, spec) is True  # 0.5% < 1%

    def test_relative_outside_tolerance(self):
        spec = relative_tolerance(0.01)
        assert _satisfies_tolerance(102.0, 100.0, spec) is False  # 2% > 1%

    def test_relative_zero_expected_uses_min_reference(self):
        # expected=0 would cause divide-by-zero; min_reference guards this
        spec = relative_tolerance(0.1, min_reference=1.0)
        # abs(0.05 - 0) / max(0, 1.0) = 0.05 / 1.0 = 0.05 <= 0.1 → True
        assert _satisfies_tolerance(0.05, 0.0, spec) is True
        # abs(0.2 - 0) / 1.0 = 0.2 > 0.1 → False
        assert _satisfies_tolerance(0.2, 0.0, spec) is False

    def test_relative_very_small_values(self):
        spec = relative_tolerance(0.001, min_reference=0.001)
        # abs(1e-6 - 0) / max(0, 0.001) = 0.001 ≤ 0.001 → True
        assert _satisfies_tolerance(1e-6, 0.0, spec) is True


# ---------------------------------------------------------------------------
# 5. EQUALITY assertion
# ---------------------------------------------------------------------------


class TestEqualityAssertion:
    def _make_engine_and_inspection(self) -> tuple:
        inspection = inspect_fixture("valid/valid_three_statement.xlsx")
        engine = AssertionEngine()
        return engine, inspection

    def _numeric_inspection(self):
        """Build a minimal fake inspection result with plain numeric cells."""
        from finance_model_testbench.models import CellData, WorksheetInspection, WorkbookInspectionResult

        def _cell(coord: str, value) -> CellData:
            return CellData(
                coordinate=coord,
                row=int("".join(filter(str.isdigit, coord))),
                column=1,
                data_type="n",
                raw_value=value,
            )

        ws = WorksheetInspection(
            title="TestSheet",
            state="visible",
            max_row=10,
            max_column=5,
            cells={
                "A1": _cell("A1", 100.0),
                "A2": _cell("A2", 100.0),
                "A3": _cell("A3", 50.0),
                "A4": _cell("A4", -100.0),
                "A5": _cell("A5", 0.0),
                "A6": _cell("A6", "text_value"),
            },
        )
        return WorkbookInspectionResult(
            file_path="fake_path",
            file_name="fake.xlsx",
            sheet_count=1,
            sheet_names=["TestSheet"],
            worksheets={"TestSheet": ws},
        )

    def test_exact_equality_pass(self):
        inspection = self._numeric_inspection()
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="TD_EQ_001",
            description="A1 == A2 (both 100)",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("TestSheet", "A1"),
                CellReference("TestSheet", "A2"),
            ],
            tolerance=exact_tolerance(),
        )
        results = engine.run(inspection, [td])
        assert results[0].status == AssertionStatus.PASS
        assert results[0].difference == pytest.approx(0.0)

    def test_equality_fail_outside_tolerance(self):
        inspection = self._numeric_inspection()
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="TD_EQ_002",
            description="A1 (100) == A3 (50) — should fail",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("TestSheet", "A1"),
                CellReference("TestSheet", "A3"),
            ],
            tolerance=absolute_tolerance(1.0),
        )
        results = engine.run(inspection, [td])
        assert results[0].status == AssertionStatus.FAIL
        assert results[0].difference == pytest.approx(50.0)

    def test_equality_within_absolute_tolerance_passes(self):
        from finance_model_testbench.models import CellData, WorksheetInspection, WorkbookInspectionResult

        def _cell(coord, val):
            return CellData(coordinate=coord, row=1, column=1, data_type="n", raw_value=val)

        ws = WorksheetInspection("S", "visible", 1, 1, {"A1": _cell("A1", 100.3), "A2": _cell("A2", 100.0)})
        inspection = WorkbookInspectionResult("p", "f.xlsx", 1, ["S"], {"S": ws})
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="TD_EQ_003",
            description="A1 (100.3) == A2 (100.0) within 0.5 absolute",
            assertion_type=AssertionType.EQUALITY,
            operands=[CellReference("S", "A1"), CellReference("S", "A2")],
            tolerance=absolute_tolerance(0.5),
        )
        result = engine.run(inspection, [td])[0]
        assert result.status == AssertionStatus.PASS

    def test_equality_negative_values(self):
        inspection = self._numeric_inspection()
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="TD_EQ_NEG",
            description="A4 (-100) == A4 (-100)",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("TestSheet", "A4"),
                CellReference("TestSheet", "A4"),
            ],
            tolerance=exact_tolerance(),
        )
        results = engine.run(inspection, [td])
        assert results[0].status == AssertionStatus.PASS

    def test_equality_with_missing_operand_returns_incomplete(self):
        inspection = self._numeric_inspection()
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="TD_EQ_MISS",
            description="A1 == Z99 (missing)",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("TestSheet", "A1"),
                CellReference("TestSheet", "Z99"),
            ],
            tolerance=exact_tolerance(),
        )
        results = engine.run(inspection, [td])
        assert results[0].status == AssertionStatus.INCOMPLETE

    def test_equality_with_non_numeric_operand_returns_incomplete(self):
        inspection = self._numeric_inspection()
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="TD_EQ_NONNUMERIC",
            description="A1 == A6 (non-numeric)",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("TestSheet", "A1"),
                CellReference("TestSheet", "A6"),
            ],
            tolerance=exact_tolerance(),
        )
        results = engine.run(inspection, [td])
        assert results[0].status == AssertionStatus.INCOMPLETE

    def test_equality_result_has_all_fields(self):
        inspection = self._numeric_inspection()
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="TD_EQ_FIELDS",
            description="Field completeness",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("TestSheet", "A1"),
                CellReference("TestSheet", "A2"),
            ],
            tolerance=exact_tolerance(),
        )
        result = engine.run(inspection, [td])[0]
        assert result.test_id == "TD_EQ_FIELDS"
        assert result.status in AssertionStatus.__members__.values()
        assert result.assertion_type == AssertionType.EQUALITY
        assert result.tolerance is not None
        assert len(result.resolved) == 2
        assert isinstance(result.message, str)
        assert len(result.message) > 0


# ---------------------------------------------------------------------------
# 6. DIFFERENCE assertion
# ---------------------------------------------------------------------------


class TestDifferenceAssertion:
    def _simple_inspection(self):
        from finance_model_testbench.models import CellData, WorksheetInspection, WorkbookInspectionResult

        def _cell(coord, val):
            return CellData(coordinate=coord, row=1, column=1, data_type="n", raw_value=val)

        ws = WorksheetInspection("S", "visible", 5, 2, {
            "A1": _cell("A1", 300.0),
            "A2": _cell("A2", 100.0),
            "A3": _cell("A3", -50.0),
            "A4": _cell("A4", 0.0),
        })
        return WorkbookInspectionResult("p", "f.xlsx", 1, ["S"], {"S": ws})

    def test_difference_pass(self):
        inspection = self._simple_inspection()
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="TD_DIFF_001",
            description="A1 - A2 == 200",
            assertion_type=AssertionType.DIFFERENCE,
            operands=[CellReference("S", "A1"), CellReference("S", "A2")],
            tolerance=exact_tolerance(),
            expected_value=200.0,
        )
        result = engine.run(inspection, [td])[0]
        assert result.status == AssertionStatus.PASS
        assert result.observed == pytest.approx(200.0)

    def test_difference_fail(self):
        inspection = self._simple_inspection()
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="TD_DIFF_002",
            description="A1 - A2 expected 150 but is 200",
            assertion_type=AssertionType.DIFFERENCE,
            operands=[CellReference("S", "A1"), CellReference("S", "A2")],
            tolerance=absolute_tolerance(1.0),
            expected_value=150.0,
        )
        result = engine.run(inspection, [td])[0]
        assert result.status == AssertionStatus.FAIL
        assert result.difference == pytest.approx(50.0)

    def test_difference_zero_expected(self):
        inspection = self._simple_inspection()
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="TD_DIFF_ZERO",
            description="A1 - A1 == 0",
            assertion_type=AssertionType.DIFFERENCE,
            operands=[CellReference("S", "A1"), CellReference("S", "A1")],
            tolerance=exact_tolerance(),
            expected_value=0.0,
        )
        result = engine.run(inspection, [td])[0]
        assert result.status == AssertionStatus.PASS

    def test_difference_negative_expected(self):
        inspection = self._simple_inspection()
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="TD_DIFF_NEG",
            description="A2 - A1 == -200",
            assertion_type=AssertionType.DIFFERENCE,
            operands=[CellReference("S", "A2"), CellReference("S", "A1")],
            tolerance=exact_tolerance(),
            expected_value=-200.0,
        )
        result = engine.run(inspection, [td])[0]
        assert result.status == AssertionStatus.PASS

    def test_difference_missing_expected_value_returns_error(self):
        inspection = self._simple_inspection()
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="TD_DIFF_NO_EV",
            description="DIFFERENCE with no expected_value",
            assertion_type=AssertionType.DIFFERENCE,
            operands=[CellReference("S", "A1"), CellReference("S", "A2")],
            tolerance=exact_tolerance(),
            expected_value=None,
        )
        result = engine.run(inspection, [td])[0]
        assert result.status == AssertionStatus.ERROR

    def test_difference_with_missing_cell_returns_incomplete(self):
        inspection = self._simple_inspection()
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="TD_DIFF_MISS",
            description="A1 - Z99 (missing)",
            assertion_type=AssertionType.DIFFERENCE,
            operands=[CellReference("S", "A1"), CellReference("S", "Z99")],
            tolerance=exact_tolerance(),
            expected_value=0.0,
        )
        result = engine.run(inspection, [td])[0]
        assert result.status == AssertionStatus.INCOMPLETE


# ---------------------------------------------------------------------------
# 7. SUM_EQUALITY assertion
# ---------------------------------------------------------------------------


class TestSumEqualityAssertion:
    def _inspection_with_three_values(self):
        from finance_model_testbench.models import CellData, WorksheetInspection, WorkbookInspectionResult

        def _cell(coord, val):
            return CellData(coordinate=coord, row=1, column=1, data_type="n", raw_value=val)

        ws = WorksheetInspection("S", "visible", 5, 2, {
            "A1": _cell("A1", 100.0),
            "A2": _cell("A2", 200.0),
            "A3": _cell("A3", 300.0),
        })
        return WorkbookInspectionResult("p", "f.xlsx", 1, ["S"], {"S": ws})

    def test_sum_equality_pass(self):
        inspection = self._inspection_with_three_values()
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="TD_SUM_001",
            description="A1 + A2 + A3 == 600",
            assertion_type=AssertionType.SUM_EQUALITY,
            operands=[
                CellReference("S", "A1"),
                CellReference("S", "A2"),
                CellReference("S", "A3"),
            ],
            tolerance=exact_tolerance(),
            expected_value=600.0,
        )
        result = engine.run(inspection, [td])[0]
        assert result.status == AssertionStatus.PASS
        assert result.observed == pytest.approx(600.0)

    def test_sum_equality_fail(self):
        inspection = self._inspection_with_three_values()
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="TD_SUM_002",
            description="A1 + A2 + A3 expected 999 but is 600",
            assertion_type=AssertionType.SUM_EQUALITY,
            operands=[
                CellReference("S", "A1"),
                CellReference("S", "A2"),
                CellReference("S", "A3"),
            ],
            tolerance=absolute_tolerance(1.0),
            expected_value=999.0,
        )
        result = engine.run(inspection, [td])[0]
        assert result.status == AssertionStatus.FAIL

    def test_sum_equality_missing_expected_value_returns_error(self):
        inspection = self._inspection_with_three_values()
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="TD_SUM_NO_EV",
            description="SUM_EQUALITY with no expected_value",
            assertion_type=AssertionType.SUM_EQUALITY,
            operands=[
                CellReference("S", "A1"),
                CellReference("S", "A2"),
            ],
            tolerance=exact_tolerance(),
            expected_value=None,
        )
        result = engine.run(inspection, [td])[0]
        assert result.status == AssertionStatus.ERROR

    def test_sum_equality_with_missing_operand_returns_incomplete(self):
        inspection = self._inspection_with_three_values()
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="TD_SUM_MISS",
            description="A1 + Z99 (missing) == 100",
            assertion_type=AssertionType.SUM_EQUALITY,
            operands=[
                CellReference("S", "A1"),
                CellReference("S", "Z99"),
            ],
            tolerance=exact_tolerance(),
            expected_value=100.0,
        )
        result = engine.run(inspection, [td])[0]
        assert result.status == AssertionStatus.INCOMPLETE


# ---------------------------------------------------------------------------
# 8. Status semantics verification
# ---------------------------------------------------------------------------


class TestStatusSemantics:
    """Verify that PASS / FAIL / ERROR / UNSUPPORTED / INCOMPLETE are all distinct."""

    def _inspection_numeric(self, a_val=100.0, b_val=100.0):
        from finance_model_testbench.models import CellData, WorksheetInspection, WorkbookInspectionResult

        def _cell(coord, val):
            return CellData(coordinate=coord, row=1, column=1, data_type="n", raw_value=val)

        ws = WorksheetInspection("S", "visible", 2, 2, {
            "A1": _cell("A1", a_val),
            "A2": _cell("A2", b_val),
        })
        return WorkbookInspectionResult("p", "f.xlsx", 1, ["S"], {"S": ws})

    def test_pass_status(self):
        inspection = self._inspection_numeric(100.0, 100.0)
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="STATUS_PASS",
            description="PASS case",
            assertion_type=AssertionType.EQUALITY,
            operands=[CellReference("S", "A1"), CellReference("S", "A2")],
            tolerance=exact_tolerance(),
        )
        assert engine.run(inspection, [td])[0].status == AssertionStatus.PASS

    def test_fail_status(self):
        inspection = self._inspection_numeric(100.0, 200.0)
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="STATUS_FAIL",
            description="FAIL case",
            assertion_type=AssertionType.EQUALITY,
            operands=[CellReference("S", "A1"), CellReference("S", "A2")],
            tolerance=absolute_tolerance(0.01),
        )
        assert engine.run(inspection, [td])[0].status == AssertionStatus.FAIL

    def test_incomplete_status_missing_cell(self):
        inspection = self._inspection_numeric(100.0, 100.0)
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="STATUS_INCOMPLETE",
            description="INCOMPLETE — missing cell",
            assertion_type=AssertionType.EQUALITY,
            operands=[CellReference("S", "A1"), CellReference("S", "Z99")],
            tolerance=exact_tolerance(),
        )
        result = engine.run(inspection, [td])[0]
        assert result.status == AssertionStatus.INCOMPLETE
        # Critical: INCOMPLETE must not be FAIL
        assert result.status != AssertionStatus.FAIL
        assert result.status != AssertionStatus.PASS

    def test_error_status_no_expected_value(self):
        inspection = self._inspection_numeric(100.0, 100.0)
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="STATUS_ERROR",
            description="ERROR — DIFFERENCE without expected_value",
            assertion_type=AssertionType.DIFFERENCE,
            operands=[CellReference("S", "A1"), CellReference("S", "A2")],
            tolerance=exact_tolerance(),
            expected_value=None,
        )
        assert engine.run(inspection, [td])[0].status == AssertionStatus.ERROR

    def test_incomplete_is_not_fail(self):
        """Fundamental requirement: INCOMPLETE ≠ FAIL."""
        inspection = self._inspection_numeric(100.0, 100.0)
        engine = AssertionEngine()
        # Force INCOMPLETE by referencing a non-existent sheet
        td = TestDefinition(
            test_id="STATUS_NE_FAIL",
            description="INCOMPLETE must not become FAIL",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("S", "A1"),
                CellReference("GhostSheet", "A1"),
            ],
            tolerance=exact_tolerance(),
        )
        result = engine.run(inspection, [td])[0]
        assert result.status == AssertionStatus.INCOMPLETE
        assert result.status.value != "FAIL"


# ---------------------------------------------------------------------------
# 9. Financial fixture assertions — valid workbook
# ---------------------------------------------------------------------------


class TestFinancialFixtureValid:
    """
    Verify financial assertions against the valid three-statement model.

    The valid fixture's plain numeric cells (Assumptions sheet) provide
    directly usable values.  Formula cells in other sheets have no cached
    numeric value because openpyxl generates files but does not calculate them.
    Therefore formula-dependent assertions correctly return INCOMPLETE.

    This demonstrates the FAIL / INCOMPLETE boundary: we do not fabricate
    a PASS or FAIL where the calculation layer has not run.
    """

    def setup_method(self):
        self.inspection = inspect_fixture("valid/valid_three_statement.xlsx")
        self.engine = AssertionEngine()

    def test_assumption_cell_equality(self):
        """Revenue growth rate equals itself — trivial but verifies plain numeric resolution."""
        td = TestDefinition(
            test_id="FIX_VALID_ASSUMP_EQ",
            description="Revenue growth rate equals itself",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("Assumptions", "B2", label="Revenue Growth Rate"),
                CellReference("Assumptions", "B2", label="Revenue Growth Rate copy"),
            ],
            tolerance=exact_tolerance(),
        )
        result = self.engine.run(self.inspection, [td])[0]
        assert result.status == AssertionStatus.PASS

    def test_formula_cell_without_cache_is_incomplete_not_fail(self):
        """
        A formula cell with no openpyxl cached value must return INCOMPLETE.
        This is the correct behaviour — the engine must not invent PASS or FAIL.
        """
        td = TestDefinition(
            test_id="FIX_VALID_FORMULA_INCOMPLETE",
            description="Formula cell with no cached value: INCOMPLETE expected",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("Income Statement", "C2", label="Revenue Current"),
                CellReference("Income Statement", "C2", label="Revenue Current B"),
            ],
            tolerance=absolute_tolerance(0.01),
        )
        result = self.engine.run(self.inspection, [td])[0]
        # Formula cells in openpyxl-generated workbooks have no cached value
        # → INCOMPLETE is correct here
        assert result.status in (AssertionStatus.PASS, AssertionStatus.INCOMPLETE)
        # It must NOT be FAIL
        assert result.status != AssertionStatus.FAIL

    def test_balance_sheet_prior_year_identity(self):
        """
        Balance Sheet prior year: Total Assets (B5) should equal Total Liabilities+Equity (B12).
        Both are formula cells; INCOMPLETE is acceptable if cached values are absent.
        """
        td = TestDefinition(
            test_id="FIX_VALID_BS_PRIOR",
            description="Prior year: Assets (B5) == Liabilities+Equity (B12)",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("Balance Sheet", "B5", label="Total Assets Prior"),
                CellReference("Balance Sheet", "B12", label="Total L+E Prior"),
            ],
            tolerance=absolute_tolerance(0.01),
        )
        result = self.engine.run(self.inspection, [td])[0]
        # Must not be FAIL on a valid model; acceptable to be PASS or INCOMPLETE
        assert result.status != AssertionStatus.FAIL, (
            f"Valid fixture returned FAIL on balance-sheet identity: {result.message}"
        )

    def test_income_statement_prior_year_plain_values(self):
        """
        Income Statement prior year: Revenue B2=1000, OpEx B3=800 are plain numeric.
        EBITDA B4 = B2-B3 is a formula cell.
        Verify the plain cells resolve correctly.
        """
        rev_ref = CellReference("Income Statement", "B2", label="Revenue Prior")
        rev_resolved = _resolve_reference(rev_ref, self.inspection)
        assert rev_resolved.kind == ResolvedValueKind.NUMERIC
        assert rev_resolved.numeric == pytest.approx(1000.0)

        opex_ref = CellReference("Income Statement", "B3", label="OpEx Prior")
        opex_resolved = _resolve_reference(opex_ref, self.inspection)
        assert opex_resolved.kind == ResolvedValueKind.NUMERIC
        assert opex_resolved.numeric == pytest.approx(800.0)


# ---------------------------------------------------------------------------
# 10. Financial fixture assertions — defective workbooks
# ---------------------------------------------------------------------------


class TestFinancialFixtureDefective:
    """
    Verify that the engine detects known defects through relationship evaluation.

    IMPORTANT: The engine evaluates financial relationships — it does NOT:
    - inspect the filename
    - look for special defect markers
    - hardcode expected failures
    - use the manifest labels to short-circuit evaluation

    Defects are detected because the assertion values violate the relationship,
    not because the file has a special name.

    Note: openpyxl-generated fixtures do not carry cached values for formula cells.
    Therefore assertions on formula cells will be INCOMPLETE unless a cell has a
    plain numeric value.  The defect in `defective_balance_sheet_imbalance.xlsx`
    is at C5 which has formula "=SUM(C2:C4)+50.0" — a formula cell.

    The plain-value defect in `defective_cash_flow_linkage.xlsx` is at B3 which
    was hardcoded to 0.0 instead of linking to the Income Statement.  This IS a
    plain numeric cell and therefore directly evaluable.
    """

    def setup_method(self):
        self.engine = AssertionEngine()

    def test_cross_statement_link_defect_detected(self):
        """
        Defective Cash Flow fixture: B3 = 0.0 (hardcoded, not linked to IS).
        Income Statement C5 = 50.0 (Depreciation, plain numeric).

        The relationship: CF!B3 == IS!C5 is FAIL on the defective fixture.
        The engine evaluates this because both cells are plain numeric.
        This defect detection is based purely on the relationship, not the filename.
        """
        inspection = inspect_fixture("defective/defective_cash_flow_linkage.xlsx")

        td = TestDefinition(
            test_id="FIX_DEF_CROSS_LINK",
            description="CF Depreciation should equal IS Depreciation",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("Cash Flow Statement", "B3", label="CF Depreciation"),
                CellReference("Income Statement", "C5", label="IS Depreciation"),
            ],
            tolerance=absolute_tolerance(0.01),
        )
        result = self.engine.run(inspection, [td])[0]
        # CF B3=0.0 (plain numeric), IS C5=50.0 (plain numeric) → FAIL
        assert result.status == AssertionStatus.FAIL, (
            f"Expected FAIL for cross-statement link defect but got "
            f"{result.status.value}: {result.message}"
        )
        assert result.difference is not None
        assert abs(result.difference) == pytest.approx(50.0, abs=0.01)

    def test_cross_statement_link_valid_fixture_passes(self):
        """
        The same assertion on the VALID fixture should PASS.
        CF B3 links to IS C5 in the valid model, and IS C5 = 50.0 (plain numeric).
        CF B3 is a formula cell; if no cached value, result is INCOMPLETE (not FAIL).
        """
        inspection = inspect_fixture("valid/valid_three_statement.xlsx")
        td = TestDefinition(
            test_id="FIX_VALID_CROSS_LINK",
            description="CF Depreciation should equal IS Depreciation (valid fixture)",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("Cash Flow Statement", "B3", label="CF Depreciation"),
                CellReference("Income Statement", "C5", label="IS Depreciation"),
            ],
            tolerance=absolute_tolerance(0.01),
        )
        result = self.engine.run(inspection, [td])[0]
        # Valid model: CF B3 is a formula (='Income Statement'!C5).
        # If openpyxl has no cached value for B3, this will be INCOMPLETE.
        # It must NOT be FAIL.
        assert result.status != AssertionStatus.FAIL, (
            f"Valid fixture returned FAIL on cross-statement link: {result.message}"
        )

    def test_income_statement_depreciation_is_plain_numeric(self):
        """IS C5 = 50.0 is plain numeric in all fixtures. Verify for defective."""
        inspection = inspect_fixture("defective/defective_cash_flow_linkage.xlsx")
        ref = CellReference("Income Statement", "C5", label="IS Depreciation")
        resolved = _resolve_reference(ref, inspection)
        assert resolved.kind == ResolvedValueKind.NUMERIC
        assert resolved.numeric == pytest.approx(50.0)

    def test_defective_cf_b3_is_plain_zero(self):
        """CF B3 in defective_cash_flow_linkage is hardcoded 0.0 (plain numeric, not formula)."""
        inspection = inspect_fixture("defective/defective_cash_flow_linkage.xlsx")
        ref = CellReference("Cash Flow Statement", "B3", label="CF Depreciation (defective)")
        resolved = _resolve_reference(ref, inspection)
        assert resolved.kind == ResolvedValueKind.NUMERIC
        assert resolved.numeric == pytest.approx(0.0)

    def test_no_filename_based_defect_detection(self):
        """
        Verify the engine makes no decisions based on the filename.
        Both the valid and defective fixtures use the same assertion definition.
        The different results (PASS vs FAIL) come from the cell values only.
        """
        # Shared assertion definition — identical for both fixtures
        td = TestDefinition(
            test_id="FIX_FILENAME_INDEPENDENCE",
            description="Same assertion, different fixtures",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("Cash Flow Statement", "B3"),
                CellReference("Income Statement", "C5"),
            ],
            tolerance=absolute_tolerance(0.01),
        )
        engine = AssertionEngine()

        inspection_valid = inspect_fixture("valid/valid_three_statement.xlsx")
        inspection_defective = inspect_fixture("defective/defective_cash_flow_linkage.xlsx")

        result_valid = engine.run(inspection_valid, [td])[0]
        result_defective = engine.run(inspection_defective, [td])[0]

        # Defective must be FAIL; valid must not be FAIL
        assert result_defective.status == AssertionStatus.FAIL
        assert result_valid.status != AssertionStatus.FAIL
        # The test definition is the same — only the inspection data differs
        assert td.test_id == result_valid.test_id == result_defective.test_id


# ---------------------------------------------------------------------------
# 11. Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_repeated_runs_produce_identical_results(self):
        """Running the same definitions against the same inspection must be idempotent."""
        inspection = inspect_fixture("valid/valid_three_statement.xlsx")
        engine = AssertionEngine()

        definitions = [
            TestDefinition(
                test_id=f"DET_{i:03d}",
                description=f"Determinism check {i}",
                assertion_type=AssertionType.EQUALITY,
                operands=[
                    CellReference("Assumptions", "B2"),
                    CellReference("Assumptions", "B2"),
                ],
                tolerance=exact_tolerance(),
            )
            for i in range(5)
        ]

        results_1 = engine.run(inspection, definitions)
        results_2 = engine.run(inspection, definitions)

        for r1, r2 in zip(results_1, results_2):
            assert r1.test_id == r2.test_id
            assert r1.status == r2.status
            assert r1.observed == r2.observed
            assert r1.expected == r2.expected
            assert r1.difference == r2.difference

    def test_result_order_is_stable(self):
        """Results must be returned in input definition order."""
        inspection = inspect_fixture("valid/valid_three_statement.xlsx")
        engine = AssertionEngine()

        ids = [f"ORD_{i:03d}" for i in range(10)]
        definitions = [
            TestDefinition(
                test_id=tid,
                description=f"Order test {tid}",
                assertion_type=AssertionType.EQUALITY,
                operands=[
                    CellReference("Assumptions", "B2"),
                    CellReference("Assumptions", "B2"),
                ],
                tolerance=exact_tolerance(),
            )
            for tid in ids
        ]

        results = engine.run(inspection, definitions)
        assert [r.test_id for r in results] == ids


# ---------------------------------------------------------------------------
# 12. Source workbook integrity (no mutation)
# ---------------------------------------------------------------------------


class TestSourceWorkbookIntegrity:
    def test_assertion_engine_does_not_mutate_source_file(self):
        """Running assertions must not alter the source workbook bytes."""
        fixture_path = get_fixture_path("valid/valid_three_statement.xlsx")
        hash_before = compute_file_hash(fixture_path)

        inspection = WorkbookInspector().inspect(fixture_path)
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="INTEGRITY_001",
            description="Source integrity check",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("Assumptions", "B2"),
                CellReference("Assumptions", "B2"),
            ],
            tolerance=exact_tolerance(),
        )
        engine.run(inspection, [td])

        hash_after = compute_file_hash(fixture_path)
        assert hash_before == hash_after, "AssertionEngine mutated the source workbook!"


# ---------------------------------------------------------------------------
# 13. Engine robustness (invalid inputs to run())
# ---------------------------------------------------------------------------


class TestEngineRobustness:
    def test_run_with_non_inspection_result_raises(self):
        engine = AssertionEngine()
        with pytest.raises(InvalidTestDefinitionError):
            engine.run("not_an_inspection_result", [])

    def test_empty_definition_list_returns_empty_results(self):
        inspection = inspect_fixture("valid/valid_three_statement.xlsx")
        engine = AssertionEngine()
        results = engine.run(inspection, [])
        assert results == []

    def test_result_model_is_json_serializable(self):
        """AssertionResult.to_dict() must produce JSON-serializable output."""
        import json

        inspection = inspect_fixture("valid/valid_three_statement.xlsx")
        engine = AssertionEngine()
        td = TestDefinition(
            test_id="JSON_001",
            description="JSON serialization test",
            assertion_type=AssertionType.EQUALITY,
            operands=[
                CellReference("Assumptions", "B2"),
                CellReference("Assumptions", "B2"),
            ],
            tolerance=absolute_tolerance(0.01),
        )
        results = engine.run(inspection, [td])
        for result in results:
            d = result.to_dict()
            serialized = json.dumps(d)  # Must not raise
            assert isinstance(serialized, str)
