"""
Finance-Model-Testbench package root.
"""

from finance_model_testbench.config import TestbenchConfig
from finance_model_testbench.inspector import WorkbookInspector
from finance_model_testbench.models import (
    WorkbookInspectionResult,
    WorksheetInspection,
    CellData,
)
from finance_model_testbench.exceptions import (
    TestbenchError,
    WorkbookInspectionError,
    InvalidInputError,
    UnsupportedFormatError,
    WorkbookLoadError,
    # C4
    AssertionEngineError,
    InvalidTestDefinitionError,
    UnsupportedAssertionError,
    ValueResolutionError,
    AssertionExecutionError,
    # C5
    ScenarioError,
    ScenarioInputError,
    RecalculationError,
    CalculationFailedError,
)
from finance_model_testbench.assertion_models import (
    AssertionStatus,
    AssertionType,
    ToleranceType,
    ToleranceSpec,
    CellReference,
    TestDefinition,
    ResolvedValue,
    ResolvedValueKind,
    AssertionResult,
    exact_tolerance,
    absolute_tolerance,
    relative_tolerance,
)
from finance_model_testbench.assertion_engine import AssertionEngine
from finance_model_testbench.scenario_models import (
    RecalculationStatus,
    ScenarioInput,
    ScenarioDefinition,
    ScenarioExecutionResult,
)
from finance_model_testbench.recalculator import WorkbookRecalculator
from finance_model_testbench.scenario_runner import ScenarioRunner
from finance_model_testbench.report_models import (
    OverallOutcome,
    ReportMetadata,
    ReportSummary,
    TestEvidence,
    TestbenchReport,
)
from finance_model_testbench.report_generator import ReportGenerator
from finance_model_testbench.benchmark import BenchmarkCase, BenchmarkRunner, benchmark_cases, load_ground_truth

__version__ = "0.1.0"
__author__ = "Finance-Model-Testbench Contributors"

