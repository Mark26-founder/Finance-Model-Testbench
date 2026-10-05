"""
Scenario runner implementation for C5 — Scenario Execution and Formula Recalculation.
"""

import hashlib
import os
from typing import Dict, List, Optional, Sequence, Tuple

from finance_model_testbench.assertion_engine import AssertionEngine
from finance_model_testbench.assertion_models import AssertionResult, TestDefinition
from finance_model_testbench.exceptions import (
    InvalidInputError,
    RecalculationError,
    ScenarioError,
    ScenarioInputError,
)
from finance_model_testbench.recalculator import WorkbookRecalculator
from finance_model_testbench.scenario_models import (
    RecalculationStatus,
    ScenarioDefinition,
    ScenarioExecutionResult,
    ScenarioInput,
)


class ScenarioRunner:
    """
    Executes controlled scenarios against financial model workbooks.
    Ensures source workbook immutability, safe temp isolation, formula recalculation,
    and rerunning of explicit C4 assertions.
    """

    def __init__(
        self,
        recalculator: Optional[WorkbookRecalculator] = None,
        assertion_engine: Optional[AssertionEngine] = None,
    ) -> None:
        self._recalculator = recalculator or WorkbookRecalculator()
        self._assertion_engine = assertion_engine or AssertionEngine()

    @staticmethod
    def _compute_sha256(file_path: str) -> str:
        """Computes SHA-256 hex digest of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def run(
        self,
        file_path: str,
        test_definitions: Sequence[TestDefinition],
        scenario: Optional[ScenarioDefinition] = None,
    ) -> ScenarioExecutionResult:
        """
        Executes a single scenario or baseline recalculation against a financial model.

        Args:
            file_path: Path to target .xlsx workbook.
            test_definitions: Sequence of TestDefinition assertions to run.
            scenario: Optional ScenarioDefinition containing assumption changes.

        Returns:
            ScenarioExecutionResult object containing recalculation status and assertion outcomes.
        """
        if not file_path or not isinstance(file_path, str):
            raise InvalidInputError("File path must be a non-empty string.")

        if not os.path.exists(file_path):
            raise InvalidInputError(f"Workbook file does not exist: {file_path}")

        if not test_definitions:
            raise InvalidInputError("test_definitions list cannot be empty.")

        for td in test_definitions:
            if not isinstance(td, TestDefinition):
                raise InvalidInputError(f"All test_definitions must be TestDefinition instances, got {type(td)}.")

        if scenario is not None and not isinstance(scenario, ScenarioDefinition):
            raise ScenarioInputError(f"Expected ScenarioDefinition, got {type(scenario)}.")

        # Record initial SHA-256 hash of source workbook
        initial_sha256 = self._compute_sha256(file_path)

        scenario_id = scenario.scenario_id if scenario else "BASELINE"
        scenario_inputs = scenario.inputs if scenario else ()

        inputs_applied: Dict[str, str] = {}
        for inp in scenario_inputs:
            key = f"'{inp.cell.sheet_name}'!{inp.cell.coordinate}"
            inputs_applied[key] = str(inp.value)

        # 1. Recalculate workbook with optional inputs
        recalculated_inspection, status, msg = self._recalculator.recalculate(
            file_path=file_path,
            inputs=scenario_inputs,
        )

        # 2. Run assertion engine against recalculated inspection result
        assertion_results = self._assertion_engine.run(
            recalculated_inspection,
            test_definitions,
        )

        # 3. Verify source file byte immutability
        final_sha256 = self._compute_sha256(file_path)
        if final_sha256 != initial_sha256:
            raise RecalculationError(
                f"SOURCE INTEGRITY VIOLATION: Source workbook file '{file_path}' was modified during scenario execution."
            )

        return ScenarioExecutionResult(
            scenario_id=scenario_id,
            source_file=file_path,
            source_sha256=initial_sha256,
            recalculation_status=status,
            recalculation_message=msg,
            assertion_results=tuple(assertion_results),
            inputs_applied=inputs_applied,
        )

    def run_scenarios(
        self,
        file_path: str,
        test_definitions: Sequence[TestDefinition],
        scenarios: Sequence[ScenarioDefinition],
    ) -> List[ScenarioExecutionResult]:
        """
        Executes multiple independent scenarios sequentially against the same source workbook.
        Each scenario runs in complete isolation starting from the original source file.

        Args:
            file_path: Path to target .xlsx workbook.
            test_definitions: Sequence of TestDefinition assertions to evaluate per scenario.
            scenarios: Sequence of ScenarioDefinition scenarios to run.

        Returns:
            List of ScenarioExecutionResult objects, one per scenario.
        """
        if not scenarios:
            raise InvalidInputError("scenarios list cannot be empty.")

        results: List[ScenarioExecutionResult] = []
        for scenario in scenarios:
            result = self.run(
                file_path=file_path,
                test_definitions=test_definitions,
                scenario=scenario,
            )
            results.append(result)

        return results
