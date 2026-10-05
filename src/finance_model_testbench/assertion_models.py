"""
C4 — Deterministic Test Engine: Data models.

Defines the immutable data structures for:
- CellReference        : explicit reference to a workbook/sheet/cell
- ToleranceSpec        : explicit tolerance with type (EXACT, ABSOLUTE, RELATIVE)
- AssertionType        : enumeration of supported assertion kinds
- TestDefinition       : a single, self-contained test specification
- AssertionStatus      : outcome enumeration (PASS, FAIL, ERROR, UNSUPPORTED, INCOMPLETE)
- ResolvedValue        : the result of resolving a CellReference against inspection data
- AssertionResult      : the structured result of executing one TestDefinition

STATUS SEMANTICS
----------------
PASS        : The condition was evaluated and satisfied.
FAIL        : The condition was evaluated and NOT satisfied.
ERROR       : An unexpected execution problem occurred during evaluation.
UNSUPPORTED : The assertion or value type is outside the supported engine scope.
INCOMPLETE  : Required information is unavailable (e.g. recalculated value needed but
              C5 has not been executed). INCOMPLETE ≠ FAIL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AssertionStatus(str, Enum):
    """
    Deterministic execution outcome for a single assertion.

    INCOMPLETE is used when required values are unavailable because computation
    (e.g. spreadsheet recalculation owned by C5) has not been performed.
    It must never be silently promoted to PASS or FAIL.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    UNSUPPORTED = "UNSUPPORTED"
    INCOMPLETE = "INCOMPLETE"


class AssertionType(str, Enum):
    """
    Supported assertion kinds.

    EQUALITY       : operand_a == operand_b  (within tolerance)
    DIFFERENCE     : operand_a - operand_b == expected_difference  (within tolerance)
    SUM_EQUALITY   : sum(operands) == expected_value  (within tolerance)
    """

    EQUALITY = "EQUALITY"
    DIFFERENCE = "DIFFERENCE"
    SUM_EQUALITY = "SUM_EQUALITY"


class ToleranceType(str, Enum):
    """
    Tolerance semantics.

    EXACT    : Values must be bitwise identical (Python ==).
    ABSOLUTE : abs(observed - expected) <= tolerance_value
    RELATIVE : abs(observed - expected) / max(abs(expected), min_reference) <= tolerance_value
               where min_reference prevents division-by-zero for near-zero expected values.
    """

    EXACT = "EXACT"
    ABSOLUTE = "ABSOLUTE"
    RELATIVE = "RELATIVE"


# ---------------------------------------------------------------------------
# Cell Reference
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CellReference:
    """
    Explicit, deterministic reference to a workbook/sheet/cell coordinate.

    The engine uses only this reference to locate values in a
    WorkbookInspectionResult; it never infers financial intent from
    sheet names or cell positions.

    Attributes
    ----------
    sheet_name : Name of the worksheet (case-sensitive, must match inspection result).
    coordinate : Excel-style cell coordinate such as ``"C5"`` or ``"B10"``.
    label      : Optional human-readable label for reporting purposes only.
                 It does NOT affect assertion logic.
    """

    sheet_name: str
    coordinate: str
    label: Optional[str] = None

    def __str__(self) -> str:
        label_part = f" ({self.label})" if self.label else ""
        return f"'{self.sheet_name}'!{self.coordinate}{label_part}"


# ---------------------------------------------------------------------------
# Tolerance specification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToleranceSpec:
    """
    Explicit tolerance definition for numeric comparisons.

    Attributes
    ----------
    tolerance_type  : EXACT, ABSOLUTE, or RELATIVE.
    tolerance_value : The numeric threshold.
                      - For EXACT: must be 0.0 (ignored).
                      - For ABSOLUTE: abs(observed - expected) <= tolerance_value.
                      - For RELATIVE: fractional threshold (e.g. 0.0001 for 0.01%).
    min_reference   : Minimum denominator guard for RELATIVE comparisons where
                      expected is zero or near-zero. Defaults to 1.0.
                      This value must be explicitly set; no hidden defaults.
    """

    tolerance_type: ToleranceType
    tolerance_value: float = 0.0
    min_reference: float = 1.0

    def __post_init__(self) -> None:
        if self.tolerance_value < 0.0:
            raise ValueError(
                f"tolerance_value must be >= 0. Got: {self.tolerance_value}"
            )
        if self.min_reference <= 0.0:
            raise ValueError(
                f"min_reference must be > 0 to guard against division by zero. "
                f"Got: {self.min_reference}"
            )

    def to_dict(self) -> dict:
        return {
            "tolerance_type": self.tolerance_type.value,
            "tolerance_value": self.tolerance_value,
            "min_reference": self.min_reference,
        }


# ---------------------------------------------------------------------------
# Convenience tolerance factories
# ---------------------------------------------------------------------------


def exact_tolerance() -> ToleranceSpec:
    """Return a EXACT tolerance specification."""
    return ToleranceSpec(tolerance_type=ToleranceType.EXACT, tolerance_value=0.0)


def absolute_tolerance(value: float) -> ToleranceSpec:
    """Return an ABSOLUTE tolerance specification."""
    return ToleranceSpec(tolerance_type=ToleranceType.ABSOLUTE, tolerance_value=value)


def relative_tolerance(fraction: float, min_reference: float = 1.0) -> ToleranceSpec:
    """
    Return a RELATIVE tolerance specification.

    Parameters
    ----------
    fraction      : Fractional threshold, e.g. 0.0001 means 0.01%.
    min_reference : Denominator guard for near-zero expected values.
    """
    return ToleranceSpec(
        tolerance_type=ToleranceType.RELATIVE,
        tolerance_value=fraction,
        min_reference=min_reference,
    )


# ---------------------------------------------------------------------------
# Test Definition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TestDefinition:
    """
    A single, self-contained financial assertion specification.

    The engine evaluates the assertion defined here against values resolved
    from an inspection result. It does NOT infer financial rules from context.

    Attributes
    ----------
    test_id        : Unique identifier for this test (e.g. ``"TD_BS_001"``).
    description    : Human-readable description of what is being tested.
    assertion_type : The kind of assertion (EQUALITY, DIFFERENCE, SUM_EQUALITY).
    operands       : Ordered list of CellReferences used as assertion inputs.
                     Interpretation depends on assertion_type:
                       EQUALITY     : [a, b]          → a == b
                       DIFFERENCE   : [a, b]           → a - b == expected_value
                       SUM_EQUALITY : [a, b, c, ...]   → sum(operands) == expected_value
    expected_value : The expected numeric result of the assertion.
                     For EQUALITY: this is the expected value of operand b
                       (and operand a must equal it).  When two operands reference
                       model cells, expected_value is the result of evaluating
                       operand_b, not a hard-coded constant.
                     For DIFFERENCE: a - b is compared to this value.
                     For SUM_EQUALITY: sum(operands) is compared to this value.
                     Set to None only for EQUALITY where both sides are cell references
                     and the equality relationship is cell_a == cell_b.
    tolerance      : Explicit numeric tolerance specification.
    tags           : Optional metadata tags for grouping/filtering.
    """

    test_id: str
    description: str
    assertion_type: AssertionType
    operands: Sequence[CellReference]
    tolerance: ToleranceSpec
    expected_value: Optional[float] = None
    tags: tuple = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.test_id or not self.test_id.strip():
            raise ValueError("test_id must be a non-empty string.")
        if not self.description or not self.description.strip():
            raise ValueError("description must be a non-empty string.")
        if not self.operands:
            raise ValueError("operands must contain at least one CellReference.")

        if self.assertion_type == AssertionType.EQUALITY:
            if len(self.operands) != 2:
                raise ValueError(
                    "EQUALITY assertion requires exactly 2 operands. "
                    f"Got {len(self.operands)}."
                )

        elif self.assertion_type == AssertionType.DIFFERENCE:
            if len(self.operands) != 2:
                raise ValueError(
                    "DIFFERENCE assertion requires exactly 2 operands [a, b] "
                    f"where a - b == expected_value. Got {len(self.operands)}."
                )

        elif self.assertion_type == AssertionType.SUM_EQUALITY:
            if len(self.operands) < 2:
                raise ValueError(
                    "SUM_EQUALITY assertion requires at least 2 operands. "
                    f"Got {len(self.operands)}."
                )

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "description": self.description,
            "assertion_type": self.assertion_type.value,
            "operands": [str(op) for op in self.operands],
            "expected_value": self.expected_value,
            "tolerance": self.tolerance.to_dict(),
            "tags": list(self.tags),
        }


# ---------------------------------------------------------------------------
# Resolved value
# ---------------------------------------------------------------------------


class ResolvedValueKind(str, Enum):
    """Classification of what was found at a cell reference."""

    NUMERIC = "NUMERIC"         # A usable numeric value
    NON_NUMERIC = "NON_NUMERIC" # A string/bool/other non-numeric value
    FORMULA_CACHED = "FORMULA_CACHED"   # Formula with openpyxl cached value
    FORMULA_NO_CACHE = "FORMULA_NO_CACHE"  # Formula with no available cached value
    MISSING = "MISSING"         # Cell or sheet not found in inspection result


@dataclass(frozen=True)
class ResolvedValue:
    """
    The result of resolving a CellReference against a WorkbookInspectionResult.

    Attributes
    ----------
    reference    : The original CellReference.
    kind         : Classification of the resolved cell.
    numeric      : The usable float value, or None if unavailable.
    raw          : The raw value as stored in the inspection result.
    formula      : The formula expression if the cell contains a formula.
    note         : Human-readable explanation of why numeric is None.
    """

    reference: CellReference
    kind: ResolvedValueKind
    numeric: Optional[float]
    raw: Any = None
    formula: Optional[str] = None
    note: Optional[str] = None

    @property
    def is_usable(self) -> bool:
        """True if a numeric value is available for assertion evaluation."""
        return self.numeric is not None

    def to_dict(self) -> dict:
        return {
            "reference": str(self.reference),
            "kind": self.kind.value,
            "numeric": self.numeric,
            "raw": str(self.raw) if self.raw is not None else None,
            "formula": self.formula,
            "note": self.note,
        }


# ---------------------------------------------------------------------------
# Assertion result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AssertionResult:
    """
    The structured result of executing a single TestDefinition.

    All fields are populated unconditionally; unavailable fields use None.
    This structure is the primary C4 output and will be consumed by C6 reporting.

    Attributes
    ----------
    test_id        : Mirrors TestDefinition.test_id.
    status         : PASS, FAIL, ERROR, UNSUPPORTED, or INCOMPLETE.
    assertion_type : Mirrors TestDefinition.assertion_type.
    expected       : The expected numeric value (if determinable).
    observed       : The computed/observed value from model data (if determinable).
    difference     : observed - expected (if both are available).
    tolerance      : Mirrors TestDefinition.tolerance.
    resolved       : Resolved values for each operand.
    message        : Concise explanation of the outcome.
    """

    test_id: str
    status: AssertionStatus
    assertion_type: AssertionType
    tolerance: ToleranceSpec
    resolved: List[ResolvedValue]
    message: str
    expected: Optional[float] = None
    observed: Optional[float] = None
    difference: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "status": self.status.value,
            "assertion_type": self.assertion_type.value,
            "expected": self.expected,
            "observed": self.observed,
            "difference": self.difference,
            "tolerance": self.tolerance.to_dict(),
            "resolved": [r.to_dict() for r in self.resolved],
            "message": self.message,
        }
