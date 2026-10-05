"""
Tests for C3 — Workbook Inspection layer.
"""

import hashlib
import os
import pytest

from finance_model_testbench.inspector import WorkbookInspector
from finance_model_testbench.exceptions import (
    InvalidInputError,
    UnsupportedFormatError,
    WorkbookLoadError,
)


def get_fixture_path(relative_subpath: str) -> str:
    return os.path.join("examples", "fixtures", relative_subpath)


def compute_file_hash(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()


def test_valid_workbook_inspection():
    """Verify loading and structured inspection of valid 3-statement workbook."""
    path = get_fixture_path("valid/valid_three_statement.xlsx")
    inspector = WorkbookInspector()
    result = inspector.inspect(path)

    assert result.file_name == "valid_three_statement.xlsx"
    assert result.sheet_count == 4
    assert result.sheet_names == ["Assumptions", "Income Statement", "Balance Sheet", "Cash Flow Statement"]

    # Check cell formula inspection vs raw value
    bs_sheet = result.worksheets["Balance Sheet"]
    assert "C5" in bs_sheet.cells
    cell_c5 = bs_sheet.cells["C5"]
    assert cell_c5.formula == "=SUM(C2:C4)"
    assert cell_c5.raw_value == "=SUM(C2:C4)"
    
    # Check JSON serializability
    d = result.to_dict()
    assert d["file_name"] == "valid_three_statement.xlsx"
    assert "Balance Sheet" in d["worksheets"]


def test_defective_workbook_inspection():
    """Verify inspector captures formulas in defective fixtures without judging correctness."""
    path = get_fixture_path("defective/defective_balance_sheet_imbalance.xlsx")
    inspector = WorkbookInspector()
    result = inspector.inspect(path)

    cell_c5 = result.get_cell("Balance Sheet", "C5")
    assert cell_c5 is not None
    assert cell_c5.formula == "=SUM(C2:C4)+50.0"


def test_scenario_workbook_inspection():
    """Verify inspection of scenario-capable workbook assumption input cells."""
    path = get_fixture_path("scenarios/scenario_three_statement.xlsx")
    inspector = WorkbookInspector()
    result = inspector.inspect(path)

    assump_sheet = result.worksheets["Assumptions"]
    assert "B2" in assump_sheet.cells
    cell_b2 = assump_sheet.cells["B2"]
    assert cell_b2.formula is None
    assert cell_b2.raw_value == 0.05


def test_source_file_integrity_preserved():
    """Verify read-only inspection does not alter the source file byte hash."""
    path = get_fixture_path("valid/valid_three_statement.xlsx")
    hash_before = compute_file_hash(path)
    
    inspector = WorkbookInspector()
    _ = inspector.inspect(path)
    
    hash_after = compute_file_hash(path)
    assert hash_before == hash_after, "Source workbook was mutated by inspection!"


def test_inspection_determinism():
    """Verify consecutive inspections of the same workbook produce identical dict outputs."""
    path = get_fixture_path("valid/valid_three_statement.xlsx")
    inspector = WorkbookInspector()
    
    res1 = inspector.inspect(path).to_dict()
    res2 = inspector.inspect(path).to_dict()
    
    assert res1 == res2


def test_error_handling_missing_file():
    """Verify InvalidInputError raised for missing file."""
    inspector = WorkbookInspector()
    with pytest.raises(InvalidInputError):
        inspector.inspect("non_existent_file.xlsx")


def test_error_handling_unsupported_extension(tmp_path):
    """Verify UnsupportedFormatError raised for non-xlsx file format."""
    bad_file = tmp_path / "test.csv"
    bad_file.write_text("a,b,c")
    inspector = WorkbookInspector()
    with pytest.raises(UnsupportedFormatError):
        inspector.inspect(str(bad_file))
