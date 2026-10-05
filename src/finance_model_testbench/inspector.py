"""
Read-only workbook inspector implementation using openpyxl.
"""

import os
import openpyxl
from openpyxl.utils import get_column_letter

from finance_model_testbench.exceptions import (
    InvalidInputError,
    UnsupportedFormatError,
    WorkbookLoadError,
    WorkbookInspectionError,
)
from finance_model_testbench.models import (
    CellData,
    WorksheetInspection,
    WorkbookInspectionResult,
)


class WorkbookInspector:
    """
    Safe, deterministic, read-only inspector for .xlsx workbooks.
    """

    SUPPORTED_EXTENSIONS = {".xlsx"}

    def inspect(self, file_path: str) -> WorkbookInspectionResult:
        """
        Loads and inspects a workbook file in read-only mode, returning a structured WorkbookInspectionResult.

        Security boundary:
        - Only .xlsx files are supported.
        - Workbooks are opened in read-only mode; VBA is explicitly ignored.
        - Original file is never modified.
        - Error messages expose only the filename, not full absolute paths.
        """
        if not file_path or not isinstance(file_path, str):
            raise InvalidInputError("File path must be a non-empty string.")

        # Reject directories before extension check
        if os.path.isdir(file_path):
            raise InvalidInputError(
                f"Expected a .xlsx file path, but a directory was supplied: '{os.path.basename(file_path) or file_path}'"
            )

        if not os.path.exists(file_path):
            raise InvalidInputError(
                f"Workbook file does not exist: '{os.path.basename(file_path) or file_path}'"
            )

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise UnsupportedFormatError(
                f"Unsupported file format '{ext}'. Only .xlsx is supported."
            )

        safe_name = os.path.basename(file_path)  # used in error messages to avoid path leakage

        # Load formulas
        try:
            wb_formulas = openpyxl.load_workbook(file_path, data_only=False, keep_vba=False, read_only=True)
        except Exception as e:
            raise WorkbookLoadError(
                f"Failed to load workbook '{safe_name}': {type(e).__name__}"
            ) from e

        # Load cached values
        try:
            wb_values = openpyxl.load_workbook(file_path, data_only=True, keep_vba=False, read_only=True)
        except Exception as e:
            raise WorkbookLoadError(
                f"Failed to load cached values for '{safe_name}': {type(e).__name__}"
            ) from e

        worksheets_dict = {}

        try:
            for sheet_name in wb_formulas.sheetnames:
                ws_form = wb_formulas[sheet_name]
                ws_val = wb_values[sheet_name] if sheet_name in wb_values.sheetnames else None

                cells_dict = {}
                max_r = ws_form.max_row or 0
                max_c = ws_form.max_column or 0

                # Iterate through used rows and columns
                for row in ws_form.iter_rows():
                    for cell_f in row:
                        if cell_f.value is None and cell_f.comment is None:
                            continue

                        coord = cell_f.coordinate
                        c_val = ws_val[coord].value if ws_val is not None else None

                        raw_val = cell_f.value
                        formula_expr = None
                        cached_val = None

                        if isinstance(raw_val, str) and raw_val.startswith("="):
                            formula_expr = raw_val
                            cached_val = c_val
                        else:
                            cached_val = None

                        cell_data = CellData(
                            coordinate=coord,
                            row=cell_f.row,
                            column=cell_f.column,
                            data_type=cell_f.data_type,
                            raw_value=raw_val,
                            formula=formula_expr,
                            cached_value=cached_val,
                            number_format=cell_f.number_format,
                        )
                        cells_dict[coord] = cell_data

                ws_inspection = WorksheetInspection(
                    title=sheet_name,
                    state=ws_form.sheet_state,
                    max_row=max_r,
                    max_column=max_c,
                    cells=cells_dict,
                )
                worksheets_dict[sheet_name] = ws_inspection

        except Exception as e:
            raise WorkbookInspectionError(
                f"Error inspecting workbook sheets in '{safe_name}': {type(e).__name__}: {str(e)}"
            ) from e
        finally:
            # Capture sheet metadata before closing workbook handles
            all_sheet_names = list(wb_formulas.sheetnames)
            wb_formulas.close()
            wb_values.close()

        file_name = os.path.basename(file_path)
        return WorkbookInspectionResult(
            file_path=file_path,
            file_name=file_name,
            sheet_count=len(all_sheet_names),
            sheet_names=all_sheet_names,
            worksheets=worksheets_dict,
        )
