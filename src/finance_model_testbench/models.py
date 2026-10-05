"""
Data structures for deterministic, read-only workbook inspection results.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass(frozen=True)
class CellData:
    """
    Immutable representation of inspected cell metadata.
    """
    coordinate: str
    row: int
    column: int
    data_type: str
    raw_value: Any
    formula: Optional[str] = None
    cached_value: Any = None
    number_format: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coordinate": self.coordinate,
            "row": self.row,
            "column": self.column,
            "data_type": self.data_type,
            "raw_value": str(self.raw_value) if self.raw_value is not None else None,
            "formula": self.formula,
            "cached_value": str(self.cached_value) if self.cached_value is not None else None,
            "number_format": self.number_format,
        }


@dataclass(frozen=True)
class WorksheetInspection:
    """
    Immutable inspection summary of an individual worksheet.
    """
    title: str
    state: str
    max_row: int
    max_column: int
    cells: Dict[str, CellData] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "state": self.state,
            "max_row": self.max_row,
            "max_column": self.max_column,
            "cell_count": len(self.cells),
            "cells": {coord: cell.to_dict() for coord, cell in sorted(self.cells.items())},
        }


@dataclass(frozen=True)
class WorkbookInspectionResult:
    """
    Structured, JSON-serializable result of a workbook inspection.
    """
    file_path: str
    file_name: str
    sheet_count: int
    sheet_names: List[str]
    worksheets: Dict[str, WorksheetInspection]

    def get_cell(self, sheet_name: str, coordinate: str) -> Optional[CellData]:
        sheet = self.worksheets.get(sheet_name)
        if sheet:
            return sheet.cells.get(coordinate)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_name": self.file_name,
            "sheet_count": self.sheet_count,
            "sheet_names": list(self.sheet_names),
            "worksheets": {title: ws.to_dict() for title, ws in sorted(self.worksheets.items())},
        }
