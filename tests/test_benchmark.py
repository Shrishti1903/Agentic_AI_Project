import pytest
from benchmark import run_benchmark

def test_benchmark_sla_compliance():
    """Verify that all PRD metrics (accuracy, latency, anomaly detection, false positives) meet SLAs."""
    report = run_benchmark()
    status = report["status"]
    metrics = report["metrics"]

    # Latency SLAs
    assert status["latency_passed"], f"Latency exceeded 2.0s: avg={metrics['avg_latency_sec']}s, p95={metrics['p95_latency_sec']}s"

    # Accuracy SLAs
    assert status["accuracy_passed"], f"Categorization accuracy below 95%: {metrics['categorization_accuracy_pct']}%"

    # False positive rate SLA
    assert status["false_positive_passed"], f"False positive rate exceeds 5%: {metrics['false_positive_rate_pct']}%"

    # Policy compliance SLA
    assert status["policy_compliance_passed"], f"Policy compliance rate below 100%: {metrics['policy_compliance_rate_pct']}%"

    # Overall benchmark
    assert status["overall_benchmark_passed"], "Overall PRD SLA benchmark check failed"
