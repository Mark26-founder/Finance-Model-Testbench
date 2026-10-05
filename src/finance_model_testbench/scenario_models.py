"""
Data models for C5 — Scenario Execution and Formula Recalculation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from finance_model_testbench.assertion_models import AssertionResult, CellReference


class RecalculationStatus(str, Enum):
    """Execution status of the recalculation engine."""
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    UNSUPPORTED = "UNSUPPORTED"
    INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True)
class ScenarioInput:
    """
    Represents a single assumption change target in a scenario.

    Attributes:
        cell: Target workbook sheet and coordinate.
        value: New value to apply to the cell.
        label: Optional descriptive label for reporting.
    """
    cell: CellReference
    value: Union[int, float, str, bool]
    label: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.cell, CellReference):
            raise TypeError("ScenarioInput.cell must be a CellReference instance.")
        if isinstance(self.value, (list, dict, set, tuple)):
            raise TypeError(f"ScenarioInput.value must be a primitive scalar, got {type(self.value)}.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cell": self.cell.to_dict(),
            "value": self.value,
            "label": self.label,
        }


@dataclass(frozen=True)
class ScenarioDefinition:
    """
    Represents a controlled test scenario with defined assumption changes.

    Attributes:
        scenario_id: Unique identifier for the scenario (e.g. "SCEN_BASE_001").
        description: Description of the scenario hypothesis or objective.
        inputs: Tuple of ScenarioInput targets to apply before recalculation.
    """
    scenario_id: str
    description: str
    inputs: Tuple[ScenarioInput, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.scenario_id or not isinstance(self.scenario_id, str):
            raise ValueError("ScenarioDefinition.scenario_id must be a non-empty string.")
        if not self.description or not isinstance(self.description, str):
            raise ValueError("ScenarioDefinition.description must be a non-empty string.")
        
        # Coerce inputs sequence into immutable tuple if passed as list
        if isinstance(self.inputs, list):
            object.__setattr__(self, "inputs", tuple(self.inputs))

        for inp in self.inputs:
            if not isinstance(inp, ScenarioInput):
                raise TypeError(f"All elements of inputs must be ScenarioInput, got {type(inp)}.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "description": self.description,
            "inputs": [inp.to_dict() for inp in self.inputs],
        }


@dataclass(frozen=True)
class ScenarioExecutionResult:
    """
    Structured outcome of running a scenario + assertion suite against a model.

    Attributes:
        scenario_id: Identifier of the executed scenario.
        source_file: Path to original source workbook.
        source_sha256: SHA-256 hash of original source workbook.
        recalculation_status: Recalculation engine status (SUCCESS, ERROR, UNSUPPORTED, INCOMPLETE).
        recalculation_message: Diagnostic explanation of recalculation status.
        assertion_results: Tuple of AssertionResult items from C4 assertion engine.
        inputs_applied: Mapping of cell target strings to applied values.
    """
    scenario_id: str
    source_file: str
    source_sha256: str
    recalculation_status: RecalculationStatus
    recalculation_message: str
    assertion_results: Tuple[AssertionResult, ...] = field(default_factory=tuple)
    inputs_applied: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.assertion_results, list):
            object.__setattr__(self, "assertion_results", tuple(self.assertion_results))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "source_file": self.source_file,
            "source_sha256": self.source_sha256,
            "recalculation_status": self.recalculation_status.value,
            "recalculation_message": self.recalculation_message,
            "inputs_applied": dict(self.inputs_applied),
            "assertion_results": [res.to_dict() for res in self.assertion_results],
        }
