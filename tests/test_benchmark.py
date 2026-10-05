import hashlib
import json
from pathlib import Path

import pytest

from finance_model_testbench import BenchmarkRunner, benchmark_cases, load_ground_truth


ROOT = Path(__file__).resolve().parents[1]


def test_cases_are_manifest_backed():
    manifest = load_ground_truth()
    ids = {entry["fixture_id"] for entry in manifest["fixtures"]}
    assert {case.fixture_id for case in benchmark_cases()} == ids


def test_benchmark_detects_defects_and_valid_baseline():
    result = BenchmarkRunner(ROOT).run()
    metrics = result["metrics"]
    assert metrics["total_cases"] == 5
    assert metrics["known_defect_detections"] == 3
    assert metrics["false_positive_count"] == 0
    assert metrics["incorrectly_classified_cases"] == 0


def test_benchmark_output_is_deterministic_and_path_safe():
    runner = BenchmarkRunner(ROOT)
    first = runner.run()
    second = runner.run()
    assert runner.to_json(first) == runner.to_json(second)
    assert str(ROOT) not in runner.to_json(first)
    json.loads(runner.to_json(first))


def test_source_fixtures_are_immutable():
    paths = [ROOT / case.relative_path for case in benchmark_cases()]
    before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    BenchmarkRunner(ROOT).run()
    after = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    assert before == after


def test_report_contains_limitations_and_matrix():
    runner = BenchmarkRunner(ROOT)
    report = runner.to_markdown(runner.run())
    assert "Detection matrix" in report
    assert "synthetic" in report.lower()
    assert "real-world detection rates" in report


def test_invalid_manifest_is_rejected(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"fixtures": "invalid"}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_ground_truth(path)
