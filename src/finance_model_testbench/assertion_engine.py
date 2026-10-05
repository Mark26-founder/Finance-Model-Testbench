"""
C4 — Deterministic Test Engine: Assertion Engine.

The AssertionEngine resolves cell references from a WorkbookInspectionResult and
evaluates explicit TestDefinitions deterministically.

ARCHITECTURE BOUNDARY
---------------------
C4 operates on VALUES already available through the C3 inspection layer.
It does NOT:
  - recalculate Excel formulas
  - invoke xlcalculator, pycel, or any external calculation engine
  - mutate workbooks
  - access the network
  - call LLMs or external services

If a value depends on formula calculation that has not yet been performed,
the engine returns INCOMPLETE — never PASS or FAIL.

FORMULA / CACHED VALUE POLICY
------------------------------
openpyxl in data_only=True mode provides "cached" formula values that were
last computed by Excel when the file was saved.  The C3 inspector captures
these as `cached_value` on CellData.

C4 treats a cached formula value as a USABLE value for assertion purposes,
but it marks the ResolvedValue kind as FORMULA_CACHED to make the data
provenance explicit.  This allows a human reviewer (and future C6 reports)
to understand that the value was not freshly recalculated.

If a formula cell has no cached value (cached_value is None), the engine
returns FORMULA_NO_CACHE kind and the assertion is INCOMPLETE.

DETERMINISM
-----------
Given identical inspection data and identical test definitions, the engine
always produces identical results.  No timestamps, random values, or external
state are used.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

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
)
from finance_model_testbench.exceptions import (
    AssertionExecutionError,
    InvalidTestDefinitionError,
)
from finance_model_testbench.models import WorkbookInspectionResult


# ---------------------------------------------------------------------------
# Value resolver
# ---------------------------------------------------------------------------


def _resolve_reference(
    ref: CellReference,
    inspection: WorkbookInspectionResult,
) -> ResolvedValue:
    """
    Resolve a CellReference against a WorkbookInspectionResult.

    Resolution logic
    ----------------
    1. If the sheet does not exist in the inspection result → MISSING.
    2. If the cell coordinate does not exist in the sheet → MISSING.
    3. If the cell has a formula:
       a. With a usable cached_value (numeric) → FORMULA_CACHED, numeric set.
       b. With a non-numeric cached_value → FORMULA_NO_CACHE.
       c. With None cached_value → FORMULA_NO_CACHE.
    4. If the cell has no formula and raw_value is numeric → NUMERIC.
    5. If the cell has no formula and raw_value is non-numeric → NON_NUMERIC.

    The engine never silently coerces strings to numbers.
    The engine never treats a blank/missing cell as zero.
    """
    # Step 1: sheet existence
    sheet = inspection.worksheets.get(ref.sheet_name)
    if sheet is None:
        return ResolvedValue(
            reference=ref,
            kind=ResolvedValueKind.MISSING,
            numeric=None,
            raw=None,
            note=f"Sheet '{ref.sheet_name}' not found in inspection result.",
        )

    # Step 2: cell existence
    cell = sheet.cells.get(ref.coordinate)
    if cell is None:
        return ResolvedValue(
            reference=ref,
            kind=ResolvedValueKind.MISSING,
            numeric=None,
            raw=None,
            note=(
                f"Cell '{ref.coordinate}' not found in sheet '{ref.sheet_name}'. "
                "Blank cells are not treated as zero."
            ),
        )

    # Step 3: formula cell
    if cell.formula is not None:
        cached = cell.cached_value
        if cached is not None and isinstance(cached, (int, float)):
            return ResolvedValue(
                reference=ref,
                kind=ResolvedValueKind.FORMULA_CACHED,
                numeric=float(cached),
                raw=cell.raw_value,
                formula=cell.formula,
                note=(
                    "Value is the openpyxl cached result from the last Excel save. "
                    "Freshly recalculated values require C5."
                ),
            )
        else:
            return ResolvedValue(
                reference=ref,
                kind=ResolvedValueKind.FORMULA_NO_CACHE,
                numeric=None,
                raw=cell.raw_value,
                formula=cell.formula,
                note=(
                    "Formula cell has no usable cached numeric value. "
                    "Assertion cannot be evaluated without C5 recalculation."
                ),
            )

    # Step 4: plain numeric cell
    raw = cell.raw_value
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return ResolvedValue(
            reference=ref,
            kind=ResolvedValueKind.NUMERIC,
            numeric=float(raw),
            raw=raw,
        )

    # Step 5: non-numeric cell
    return ResolvedValue(
        reference=ref,
        kind=ResolvedValueKind.NON_NUMERIC,
        numeric=None,
        raw=raw,
        note=f"Cell value is non-numeric ({type(raw).__name__}): {raw!r}",
    )


# ---------------------------------------------------------------------------
# Tolerance evaluator
# ---------------------------------------------------------------------------


def _satisfies_tolerance(
    observed: float,
    expected: float,
    spec: ToleranceSpec,
) -> bool:
    """
    Return True if observed satisfies the tolerance specification against expected.

    EXACT    : observed == expected  (Python float equality)
    ABSOLUTE : abs(observed - expected) <= spec.tolerance_value
    RELATIVE : abs(observed - expected) / max(abs(expected), spec.min_reference)
               <= spec.tolerance_value
    """
    diff = observed - expected

    if spec.tolerance_type == ToleranceType.EXACT:
        return observed == expected

    if spec.tolerance_type == ToleranceType.ABSOLUTE:
        return abs(diff) <= spec.tolerance_value

    if spec.tolerance_type == ToleranceType.RELATIVE:
        denominator = max(abs(expected), spec.min_reference)
        return abs(diff) / denominator <= spec.tolerance_value

    # Should not reach here; all enum members handled above
    return False


# ---------------------------------------------------------------------------
# Individual assertion evaluators
# ---------------------------------------------------------------------------


def _evaluate_equality(
    definition: TestDefinition,
    resolved: List[ResolvedValue],
) -> AssertionResult:
    """
    EQUALITY: operand_a value == operand_b value, within tolerance.

    Both operand values must be numerically available.
    If either is unavailable, the result is INCOMPLETE.
    """
    rv_a, rv_b = resolved[0], resolved[1]

    if not rv_a.is_usable or not rv_b.is_usable:
        missing_refs = [
            str(r.reference) for r in [rv_a, rv_b] if not r.is_usable
        ]
        return AssertionResult(
            test_id=definition.test_id,
            status=AssertionStatus.INCOMPLETE,
            assertion_type=definition.assertion_type,
            tolerance=definition.tolerance,
            resolved=resolved,
            message=(
                f"INCOMPLETE: Cannot evaluate equality — "
                f"value(s) unavailable for: {', '.join(missing_refs)}. "
                "Recalculation (C5) may be required."
            ),
        )

    observed = rv_a.numeric
    expected = rv_b.numeric
    difference = observed - expected

    passes = _satisfies_tolerance(observed, expected, definition.tolerance)

    return AssertionResult(
        test_id=definition.test_id,
        status=AssertionStatus.PASS if passes else AssertionStatus.FAIL,
        assertion_type=definition.assertion_type,
        tolerance=definition.tolerance,
        resolved=resolved,
        expected=expected,
        observed=observed,
        difference=difference,
        message=(
            f"{'PASS' if passes else 'FAIL'}: "
            f"{str(rv_a.reference)} = {observed} "
            f"{'==' if passes else '≠'} "
            f"{str(rv_b.reference)} = {expected} "
            f"(difference: {difference}, tolerance: {definition.tolerance.tolerance_type.value} "
            f"{definition.tolerance.tolerance_value})"
        ),
    )


def _evaluate_difference(
    definition: TestDefinition,
    resolved: List[ResolvedValue],
) -> AssertionResult:
    """
    DIFFERENCE: (operand_a - operand_b) == expected_value, within tolerance.

    Both operand values must be numerically available.
    expected_value must be set on the TestDefinition.
    """
    rv_a, rv_b = resolved[0], resolved[1]

    if not rv_a.is_usable or not rv_b.is_usable:
        missing_refs = [
            str(r.reference) for r in [rv_a, rv_b] if not r.is_usable
        ]
        return AssertionResult(
            test_id=definition.test_id,
            status=AssertionStatus.INCOMPLETE,
            assertion_type=definition.assertion_type,
            tolerance=definition.tolerance,
            resolved=resolved,
            message=(
                f"INCOMPLETE: Cannot evaluate difference — "
                f"value(s) unavailable for: {', '.join(missing_refs)}."
            ),
        )

    expected = definition.expected_value
    if expected is None:
        return AssertionResult(
            test_id=definition.test_id,
            status=AssertionStatus.ERROR,
            assertion_type=definition.assertion_type,
            tolerance=definition.tolerance,
            resolved=resolved,
            message=(
                "ERROR: DIFFERENCE assertion requires expected_value to be set "
                "on the TestDefinition."
            ),
        )

    observed = rv_a.numeric - rv_b.numeric
    difference = observed - expected

    passes = _satisfies_tolerance(observed, expected, definition.tolerance)

    return AssertionResult(
        test_id=definition.test_id,
        status=AssertionStatus.PASS if passes else AssertionStatus.FAIL,
        assertion_type=definition.assertion_type,
        tolerance=definition.tolerance,
        resolved=resolved,
        expected=expected,
        observed=observed,
        difference=difference,
        message=(
            f"{'PASS' if passes else 'FAIL'}: "
            f"({str(rv_a.reference)} - {str(rv_b.reference)}) = {observed} "
            f"{'==' if passes else '≠'} expected {expected} "
            f"(difference: {difference})"
        ),
    )


def _evaluate_sum_equality(
    definition: TestDefinition,
    resolved: List[ResolvedValue],
) -> AssertionResult:
    """
    SUM_EQUALITY: sum(all operands) == expected_value, within tolerance.

    All operand values must be numerically available.
    expected_value must be set on the TestDefinition.
    """
    unavailable = [r for r in resolved if not r.is_usable]
    if unavailable:
        missing_refs = [str(r.reference) for r in unavailable]
        return AssertionResult(
            test_id=definition.test_id,
            status=AssertionStatus.INCOMPLETE,
            assertion_type=definition.assertion_type,
            tolerance=definition.tolerance,
            resolved=resolved,
            message=(
                f"INCOMPLETE: Cannot evaluate sum — "
                f"value(s) unavailable for: {', '.join(missing_refs)}."
            ),
        )

    expected = definition.expected_value
    if expected is None:
        return AssertionResult(
            test_id=definition.test_id,
            status=AssertionStatus.ERROR,
            assertion_type=definition.assertion_type,
            tolerance=definition.tolerance,
            resolved=resolved,
            message=(
                "ERROR: SUM_EQUALITY assertion requires expected_value to be set "
                "on the TestDefinition."
            ),
        )

    observed = sum(r.numeric for r in resolved)
    difference = observed - expected

    passes = _satisfies_tolerance(observed, expected, definition.tolerance)

    operand_parts = " + ".join(
        f"{str(r.reference)}={r.numeric}" for r in resolved
    )
    return AssertionResult(
        test_id=definition.test_id,
        status=AssertionStatus.PASS if passes else AssertionStatus.FAIL,
        assertion_type=definition.assertion_type,
        tolerance=definition.tolerance,
        resolved=resolved,
        expected=expected,
        observed=observed,
        difference=difference,
        message=(
            f"{'PASS' if passes else 'FAIL'}: "
            f"sum({operand_parts}) = {observed} "
            f"{'==' if passes else '≠'} expected {expected} "
            f"(difference: {difference})"
        ),
    )


# ---------------------------------------------------------------------------
# Public engine
# ---------------------------------------------------------------------------


class AssertionEngine:
    """
    Deterministic financial assertion engine (C4).

    Evaluates a list of TestDefinitions against a WorkbookInspectionResult and
    produces structured AssertionResult objects.

    This engine is stateless.  The same inputs always produce the same outputs.

    Usage
    -----
    ::

        engine = AssertionEngine()
        results = engine.run(inspection_result, test_definitions)
        for result in results:
            print(result.test_id, result.status.value)

    The engine does NOT recalculate formulas (that is C5's responsibility).
    It uses only the values already present in the WorkbookInspectionResult.
    """

    # Assertion types that the engine currently supports
    _SUPPORTED_TYPES = frozenset(AssertionType)

    def run(
        self,
        inspection: WorkbookInspectionResult,
        definitions: Sequence[TestDefinition],
    ) -> List[AssertionResult]:
        """
        Execute all test definitions against the inspection result.

        Parameters
        ----------
        inspection  : A WorkbookInspectionResult produced by C3 WorkbookInspector.
        definitions : An ordered sequence of TestDefinition objects.

        Returns
        -------
        A list of AssertionResult objects, one per definition, in input order.
        The list is never shorter than the input; every definition produces a result.

        Raises
        ------
        InvalidTestDefinitionError : If a definition is structurally invalid in a way
                                     not caught by TestDefinition.__post_init__.
        AssertionExecutionError    : For unexpected engine-level failures.
        """
        if not isinstance(inspection, WorkbookInspectionResult):
            raise InvalidTestDefinitionError(
                "inspection must be a WorkbookInspectionResult instance."
            )

        results: List[AssertionResult] = []
        for definition in definitions:
            result = self._execute_one(inspection, definition)
            results.append(result)

        return results

    def _execute_one(
        self,
        inspection: WorkbookInspectionResult,
        definition: TestDefinition,
    ) -> AssertionResult:
        """Execute a single TestDefinition. Returns an AssertionResult under all conditions."""
        try:
            return self._dispatch(inspection, definition)
        except (InvalidTestDefinitionError, AssertionExecutionError):
            raise
        except Exception as exc:
            # Catch unexpected errors and wrap them in a structured ERROR result
            return AssertionResult(
                test_id=definition.test_id,
                status=AssertionStatus.ERROR,
                assertion_type=definition.assertion_type,
                tolerance=definition.tolerance,
                resolved=[],
                message=f"ERROR: Unexpected exception during assertion execution: {exc!r}",
            )

    def _dispatch(
        self,
        inspection: WorkbookInspectionResult,
        definition: TestDefinition,
    ) -> AssertionResult:
        """Resolve values and dispatch to the appropriate assertion evaluator."""
        # Validate assertion type support
        if definition.assertion_type not in self._SUPPORTED_TYPES:
            return AssertionResult(
                test_id=definition.test_id,
                status=AssertionStatus.UNSUPPORTED,
                assertion_type=definition.assertion_type,
                tolerance=definition.tolerance,
                resolved=[],
                message=(
                    f"UNSUPPORTED: Assertion type '{definition.assertion_type.value}' "
                    "is not supported by this engine version."
                ),
            )

        # Resolve all operand references
        resolved = [
            _resolve_reference(ref, inspection)
            for ref in definition.operands
        ]

        # Dispatch to type-specific evaluator
        if definition.assertion_type == AssertionType.EQUALITY:
            return _evaluate_equality(definition, resolved)

        if definition.assertion_type == AssertionType.DIFFERENCE:
            return _evaluate_difference(definition, resolved)

        if definition.assertion_type == AssertionType.SUM_EQUALITY:
            return _evaluate_sum_equality(definition, resolved)

        # Defensive: should not reach here given _SUPPORTED_TYPES check
        return AssertionResult(
            test_id=definition.test_id,
            status=AssertionStatus.UNSUPPORTED,
            assertion_type=definition.assertion_type,
            tolerance=definition.tolerance,
            resolved=resolved,
            message=(
                f"UNSUPPORTED: No evaluator registered for assertion type "
                f"'{definition.assertion_type.value}'."
            ),
        )
