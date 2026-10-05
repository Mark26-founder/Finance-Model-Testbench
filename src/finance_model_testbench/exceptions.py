"""
Custom exception hierarchy for Finance-Model-Testbench.

C3 — Workbook Inspection exceptions:
    WorkbookInspectionError (base)
    InvalidInputError
    UnsupportedFormatError
    WorkbookLoadError

C4 — Deterministic Test Engine exceptions:
    AssertionEngineError (base)
    InvalidTestDefinitionError
    UnsupportedAssertionError
    ValueResolutionError
    AssertionExecutionError
"""


class TestbenchError(Exception):
    """Base exception for all testbench errors."""
    pass


# ---------------------------------------------------------------------------
# C3 — Workbook Inspection
# ---------------------------------------------------------------------------


class WorkbookInspectionError(TestbenchError):
    """Base exception for workbook inspection failures."""
    pass


class InvalidInputError(WorkbookInspectionError):
    """Raised when the input file path is missing, unreadable, or invalid."""
    pass


class UnsupportedFormatError(WorkbookInspectionError):
    """Raised when the input file format/extension is not supported."""
    pass


class WorkbookLoadError(WorkbookInspectionError):
    """Raised when openpyxl fails to load or parse the workbook file."""
    pass


# ---------------------------------------------------------------------------
# C4 — Deterministic Test Engine
# ---------------------------------------------------------------------------


class AssertionEngineError(TestbenchError):
    """Base exception for assertion engine failures."""
    pass


class InvalidTestDefinitionError(AssertionEngineError):
    """
    Raised when a TestDefinition is structurally invalid and cannot be evaluated.
    Examples: missing test_id, incompatible operand count for the assertion type.
    """
    pass


class UnsupportedAssertionError(AssertionEngineError):
    """
    Raised when an assertion type is not supported by the current engine version.
    Prefer returning AssertionStatus.UNSUPPORTED in a result object where possible;
    use this exception only for irrecoverable structural mismatches.
    """
    pass


class ValueResolutionError(AssertionEngineError):
    """
    Raised when a CellReference cannot be resolved due to an unexpected engine error
    (distinct from a simply missing cell, which produces ResolvedValueKind.MISSING).
    """
    pass


class AssertionExecutionError(AssertionEngineError):
    """
    Raised for unexpected engine-level failures during assertion evaluation
    that cannot be captured in a structured AssertionResult.
    """
    pass


# ---------------------------------------------------------------------------
# C5 — Scenario Execution & Formula Recalculation
# ---------------------------------------------------------------------------


class ScenarioError(TestbenchError):
    """Base exception for scenario execution failures."""
    pass


class ScenarioInputError(ScenarioError):
    """Raised when a scenario input specifies invalid cell targets or incompatible values."""
    pass


class RecalculationError(ScenarioError):
    """Base exception for formula recalculation engine failures."""
    pass


class CalculationFailedError(RecalculationError):
    """Raised when formula recalculation fails for a workbook or specific cell."""
    pass

