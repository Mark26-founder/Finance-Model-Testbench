"""
Formula recalculation engine for C5 — Scenario Execution and Formula Recalculation.
"""

import os
import re
import shutil
import tempfile
from typing import Any, Dict, List, Optional, Tuple, Union

import openpyxl
from xlcalculator import ModelCompiler, Evaluator

from finance_model_testbench.exceptions import (
    CalculationFailedError,
    InvalidInputError,
    RecalculationError,
    ScenarioInputError,
    WorkbookInspectionError,
)
from finance_model_testbench.inspector import WorkbookInspector
from finance_model_testbench.models import (
    CellData,
    WorkbookInspectionResult,
    WorksheetInspection,
)
from finance_model_testbench.scenario_models import (
    RecalculationStatus,
    ScenarioInput,
)

# Regular expression to validate standard cell coordinates like "A1", "C12", "AA100"
COORD_REGEX = re.compile(r"^[A-Za-z]+[1-9][0-9]*$")

# List of common Excel error strings
EXCEL_ERRORS = {"#REF!", "#VALUE!", "#N/A", "#NAME?", "#DIV/0!", "#NUM!", "#NULL!", "#CALC!"}


class WorkbookRecalculator:
    """
    Local formula recalculation engine using xlcalculator.
    Applies scenario assumption changes, evaluates formula graphs, and produces
    a WorkbookInspectionResult with freshly calculated numeric values.
    """

    def __init__(self, inspector: Optional[WorkbookInspector] = None) -> None:
        self._inspector = inspector or WorkbookInspector()

    def recalculate(
        self,
        file_path: str,
        inputs: Optional[Tuple[ScenarioInput, ...]] = None,
    ) -> Tuple[WorkbookInspectionResult, RecalculationStatus, str]:
        """
        Applies optional scenario inputs, recalculates all workbook formulas,
        and returns updated WorkbookInspectionResult, status, and message.

        Args:
            file_path: Absolute or relative path to .xlsx workbook.
            inputs: Optional tuple of ScenarioInput targets to apply.

        Returns:
            Tuple of (recalculated_inspection_result, RecalculationStatus, diagnostic_message).
        """
        if not file_path or not isinstance(file_path, str):
            raise InvalidInputError("File path must be a non-empty string.")

        if not os.path.exists(file_path):
            raise InvalidInputError(
                f"Workbook file does not exist: '{os.path.basename(file_path) or file_path}'"
            )

        # Validate scenario inputs before creating temp file
        inputs_tuple = inputs or ()
        for inp in inputs_tuple:
            if not isinstance(inp, ScenarioInput):
                raise ScenarioInputError(f"Expected ScenarioInput, got {type(inp)}.")
            if not COORD_REGEX.match(inp.cell.coordinate):
                raise ScenarioInputError(f"Invalid cell coordinate '{inp.cell.coordinate}' in scenario input.")

        # Create isolated temporary directory and copy of the source workbook
        temp_dir = tempfile.mkdtemp(prefix="fmt_recalc_")
        temp_path = os.path.join(temp_dir, os.path.basename(file_path))

        try:
            shutil.copy2(file_path, temp_path)

            # 1. Apply scenario inputs if provided
            if inputs_tuple:
                try:
                    wb = openpyxl.load_workbook(temp_path, data_only=False, keep_vba=False)
                except Exception as e:
                    raise WorkbookInspectionError(f"Failed to load temp workbook to apply inputs: {e}") from e

                try:
                    for inp in inputs_tuple:
                        sheet_name = inp.cell.sheet_name
                        if sheet_name not in wb.sheetnames:
                            raise ScenarioInputError(
                                f"Scenario target sheet '{sheet_name}' does not exist in workbook. "
                                f"Available sheets: {wb.sheetnames}"
                            )
                        ws = wb[sheet_name]
                        ws[inp.cell.coordinate] = inp.value

                    wb.save(temp_path)
                finally:
                    wb.close()

            # 2. Inspect base structure from modified temp file
            base_inspection = self._inspector.inspect(temp_path)

            # 3. Parse formula model with xlcalculator
            try:
                compiler = ModelCompiler()
                model = compiler.read_and_parse_archive(temp_path)
                evaluator = Evaluator(model)
            except Exception as e:
                return (
                    base_inspection,
                    RecalculationStatus.UNSUPPORTED,
                    f"Recalculation engine failed to parse workbook: {type(e).__name__}",
                )

            # 4. Recalculate formula cells across all worksheets
            updated_worksheets: Dict[str, WorksheetInspection] = {}
            recalc_errors: List[str] = []

            for sheet_name, ws_inspection in base_inspection.worksheets.items():
                updated_cells: Dict[str, CellData] = {}

                for coord, cell in ws_inspection.cells.items():
                    new_cached_value = cell.cached_value

                    if cell.formula is not None:
                        # Construct xlcalculator address key (xlcalculator uses SheetName!Coord format without quotes)
                        addr_key = f"{sheet_name}!{coord}"
                        try:
                            val = evaluator.evaluate(addr_key)
                            if hasattr(val, "value"):
                                val = val.value

                            if isinstance(val, (int, float)) and not isinstance(val, bool):
                                new_cached_value = float(val)
                            elif isinstance(val, bool):
                                new_cached_value = val
                            elif str(val) in EXCEL_ERRORS:
                                recalc_errors.append(f"{sheet_name}!{coord} formula error: {val}")
                                new_cached_value = None
                            else:
                                new_cached_value = val
                        except Exception as eval_err:
                            # Sanitize: expose only exception type, not repr (which may include temp paths)
                            recalc_errors.append(
                                f"{sheet_name}!{coord} evaluation failure: {type(eval_err).__name__}: {eval_err}"
                            )
                            new_cached_value = None

                    updated_cell = CellData(
                        coordinate=cell.coordinate,
                        row=cell.row,
                        column=cell.column,
                        data_type=cell.data_type,
                        raw_value=cell.raw_value,
                        formula=cell.formula,
                        cached_value=new_cached_value,
                        number_format=cell.number_format,
                    )
                    updated_cells[coord] = updated_cell

                updated_worksheets[sheet_name] = WorksheetInspection(
                    title=ws_inspection.title,
                    state=ws_inspection.state,
                    max_row=ws_inspection.max_row,
                    max_column=ws_inspection.max_column,
                    cells=updated_cells,
                )

            # Construct updated inspection result
            recalculated_inspection = WorkbookInspectionResult(
                file_path=file_path,  # Report original file path for provenance
                file_name=os.path.basename(file_path),
                sheet_count=len(updated_worksheets),
                sheet_names=list(updated_worksheets.keys()),
                worksheets=updated_worksheets,
            )

            if recalc_errors:
                status = RecalculationStatus.ERROR
                # Cap reported errors to 5 entries to avoid excessively large diagnostic messages
                reported = recalc_errors[:5]
                tail = f" (and {len(recalc_errors) - 5} more)" if len(recalc_errors) > 5 else ""
                msg = f"Recalculation completed with {len(recalc_errors)} cell evaluation error(s): " + "; ".join(reported) + tail
            else:
                status = RecalculationStatus.SUCCESS
                msg = "Recalculation completed successfully."

            return recalculated_inspection, status, msg

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
