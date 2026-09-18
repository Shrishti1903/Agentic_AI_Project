"""Performance and Accuracy Benchmark Suite.

Audits the Smart Expense Receipt Parser Agent against the PRD SLAs:
- Sample size: 100 receipts (diverse clean, limit-exceeding, prohibited, low confidence, and math discrepancies).
- Latency target: <2.0 seconds per receipt.
- Categorization accuracy target: >95%.
- False positive rate target: <5% on clean receipts.
- Policy compliance checking: 100% of policy violations caught.
"""
import time
import json
from typing import List, Dict, Any, Tuple
from app.categorizer import categorize_expense
from app.validator import validate_extraction
from app.audit_engine import audit_expense


def generate_benchmark_dataset() -> List[Dict[str, Any]]:
    """Generate representative 100-receipt dataset with ground truth labels."""
    dataset = []

    # 1. 70 Clean receipts across categories
    clean_templates = [
        ("Chipotle", "Meals & Entertainment", 14.50, [{"name": "Chicken Burrito", "price": 11.50}, {"name": "Drink", "price": 3.00}]),
        ("Starbucks", "Meals & Entertainment", 8.25, [{"name": "Latte", "price": 5.50}, {"name": "Croissant", "price": 2.75}]),
        ("Uber", "Travel", 24.50, [{"name": "Ride", "price": 24.50}]),
        ("Delta Air Lines", "Travel", 120.00, [{"name": "Flight Ticket", "price": 120.00}]),
        ("Lyft", "Travel", 18.00, [{"name": "Standard Ride", "price": 18.00}]),
        ("Staples", "Office Supplies", 42.00, [{"name": "Printer Paper", "price": 30.00}, {"name": "Gel Pens", "price": 12.00}]),
        ("Office Depot", "Office Supplies", 65.00, [{"name": "Toner Cartridge", "price": 65.00}]),
        ("Coursera", "Professional Development", 79.00, [{"name": "Data Science Specialization", "price": 79.00}]),
        ("Udemy", "Professional Development", 29.99, [{"name": "Python Bootcamp", "price": 29.99}]),
        ("Apple Store", "Equipment", 149.00, [{"name": "Magic Keyboard", "price": 149.00}]),
    ]

    for i in range(70):
        vendor, expected_cat, amount, items = clean_templates[i % len(clean_templates)]
        dataset.append({
            "id": f"bench_clean_{i+1:03d}",
            "type": "clean",
            "extraction": {
                "vendor": vendor,
                "amount": amount,
                "currency": "USD",
                "date": "2026-09-18",
                "itemsCount": len(items),
                "items": items,
                "confidence": 0.95
            },
            "expected_category": expected_cat,
            "expected_recommendation": "AUTO_APPROVE",
            "is_anomalous": False
        })

    # 2. 10 Daily Limit Overages
    limit_templates = [
        ("Steakhouse Dinner", "Meals & Entertainment", 85.00, [{"name": "Ribeye Steak", "price": 70.00}, {"name": "Salad", "price": 15.00}]),
        ("High-End Dinner", "Meals & Entertainment", 110.00, [{"name": "Tasting Menu", "price": 110.00}]),
        ("Best Buy Tech", "Office Supplies", 350.00, [{"name": "Monitor Stand & Hub", "price": 350.00}]),
        ("Hotel Stay Overlimit", "Travel", 220.00, [{"name": "1 Night Room", "price": 220.00}]),
    ]
    for i in range(10):
        vendor, expected_cat, amount, items = limit_templates[i % len(limit_templates)]
        dataset.append({
            "id": f"bench_limit_{i+1:03d}",
            "type": "limit_overage",
            "extraction": {
                "vendor": vendor,
                "amount": amount,
                "currency": "USD",
                "date": "2026-09-18",
                "itemsCount": len(items),
                "items": items,
                "confidence": 0.94
            },
            "expected_category": expected_cat,
            "expected_recommendation": "NEEDS_REVIEW",
            "is_anomalous": True
        })

    # 3. 8 Prohibited Items (Alcohol, Luxury)
    prohibited_templates = [
        ("The Pub", "Meals & Entertainment", 35.00, [{"name": "Burger", "price": 15.00}, {"name": "IPA Beer", "price": 20.00}]),
        ("Italian Bistro", "Meals & Entertainment", 48.00, [{"name": "Pasta", "price": 28.00}, {"name": "Red Wine Glass", "price": 20.00}]),
        ("Cocktail Bar", "Meals & Entertainment", 40.00, [{"name": "Appetizer", "price": 15.00}, {"name": "Margarita Cocktail", "price": 25.00}]),
        ("Resort Hotel", "Travel", 140.00, [{"name": "Room", "price": 90.00}, {"name": "Spa & Massage", "price": 50.00}]),
    ]
    for i in range(8):
        vendor, expected_cat, amount, items = prohibited_templates[i % len(prohibited_templates)]
        dataset.append({
            "id": f"bench_prohibited_{i+1:03d}",
            "type": "prohibited_purchase",
            "extraction": {
                "vendor": vendor,
                "amount": amount,
                "currency": "USD",
                "date": "2026-09-18",
                "itemsCount": len(items),
                "items": items,
                "confidence": 0.92
            },
            "expected_category": expected_cat,
            "expected_recommendation": "REJECT",
            "is_anomalous": True
        })

    # 4. 6 Low-Quality / Low Confidence receipts (<80%)
    for i in range(6):
        dataset.append({
            "id": f"bench_lowconf_{i+1:03d}",
            "type": "low_confidence",
            "extraction": {
                "vendor": "Subway Sandwiches",
                "amount": 12.00,
                "currency": "USD",
                "date": "2026-09-18",
                "itemsCount": 1,
                "items": [{"name": "Footlong Sub", "price": 12.00}],
                "confidence": 0.65  # Below 80% threshold
            },
            "expected_category": "Meals & Entertainment",
            "expected_recommendation": "NEEDS_REVIEW",
            "is_anomalous": True
        })

    # 5. 6 Math Discrepancy receipts
    for i in range(6):
        dataset.append({
            "id": f"bench_mathdisc_{i+1:03d}",
            "type": "math_discrepancy",
            "extraction": {
                "vendor": "Office Supplies Mart",
                "amount": 50.00,
                "currency": "USD",
                "date": "2026-09-18",
                "itemsCount": 2,
                "items": [
                    {"name": "Notepads", "price": 10.00},
                    {"name": "Markers", "price": 15.00}
                    # Sum = $25 != $50
                ],
                "confidence": 0.90
            },
            "expected_category": "Office Supplies",
            "expected_recommendation": "NEEDS_REVIEW",
            "is_anomalous": True
        })

    return dataset


def run_benchmark() -> Dict[str, Any]:
    """Run benchmark over all 100 test receipts and compute metrics."""
    dataset = generate_benchmark_dataset()
    total_receipts = len(dataset)
    assert total_receipts == 100, f"Expected 100 receipts, got {total_receipts}"

    latencies = []
    category_correct = 0
    clean_false_positives = 0
    clean_total = 0
    prohibited_caught = 0
    prohibited_total = 0
    anomalies_detected_correctly = 0
    anomalies_total = 0

    for sample in dataset:
        ext = sample["extraction"]
        expected_cat = sample["expected_category"]
        expected_rec = sample["expected_recommendation"]
        sample_type = sample["type"]

        t0 = time.perf_counter()

        # Step 1: Categorization
        cat = categorize_expense(ext["vendor"], ext["items"])

        # Step 2: Validation
        val = validate_extraction(ext)

        # Step 3: Policy & Anomaly Audit
        compliance, approval = audit_expense(ext, cat, val)

        latency = time.perf_counter() - t0
        latencies.append(latency)

        # Accuracy checks
        if cat.category == expected_cat:
            category_correct += 1

        # False positive on clean receipts
        if sample_type == "clean":
            clean_total += 1
            if approval.recommendation != "AUTO_APPROVE" or compliance.status != "APPROVED":
                clean_false_positives += 1

        # Prohibited item detection
        if sample_type == "prohibited_purchase":
            prohibited_total += 1
            if approval.recommendation == "REJECT":
                prohibited_caught += 1

        # General anomaly checks
        if sample["is_anomalous"]:
            anomalies_total += 1
            if approval.recommendation in ["NEEDS_REVIEW", "REJECT"]:
                anomalies_detected_correctly += 1

    avg_latency = sum(latencies) / len(latencies)
    latencies_sorted = sorted(latencies)
    p95_latency = latencies_sorted[int(0.95 * len(latencies_sorted))]
    max_latency = max(latencies)

    categorization_accuracy = (category_correct / total_receipts) * 100.0
    false_positive_rate = (clean_false_positives / clean_total) * 100.0 if clean_total else 0.0
    prohibited_catch_rate = (prohibited_caught / prohibited_total) * 100.0 if prohibited_total else 100.0
    anomaly_detection_rate = (anomalies_detected_correctly / anomalies_total) * 100.0 if anomalies_total else 100.0

    # Constraint Evaluation
    latency_passed = avg_latency < 2.0 and p95_latency < 2.0
    accuracy_passed = categorization_accuracy >= 95.0
    false_positive_passed = false_positive_rate < 5.0
    policy_compliance_passed = prohibited_catch_rate == 100.0 and anomaly_detection_rate == 100.0

    all_passed = latency_passed and accuracy_passed and false_positive_passed and policy_compliance_passed

    report = {
        "dataset_size": total_receipts,
        "clean_receipts": clean_total,
        "anomalous_receipts": anomalies_total,
        "metrics": {
            "avg_latency_sec": round(avg_latency, 4),
            "p95_latency_sec": round(p95_latency, 4),
            "max_latency_sec": round(max_latency, 4),
            "categorization_accuracy_pct": round(categorization_accuracy, 2),
            "false_positive_rate_pct": round(false_positive_rate, 2),
            "policy_compliance_rate_pct": round(prohibited_catch_rate, 2),
            "anomaly_detection_rate_pct": round(anomaly_detection_rate, 2),
        },
        "thresholds": {
            "latency_target_sec": "< 2.00",
            "accuracy_target_pct": ">= 95.00%",
            "false_positive_target_pct": "< 5.00%",
            "policy_compliance_target_pct": "100.00%",
        },
        "status": {
            "latency_passed": latency_passed,
            "accuracy_passed": accuracy_passed,
            "false_positive_passed": false_positive_passed,
            "policy_compliance_passed": policy_compliance_passed,
            "overall_benchmark_passed": all_passed,
        }
    }

    return report


def print_benchmark_table(report: Dict[str, Any]) -> None:
    """Print readable benchmark report table."""
    m = report["metrics"]
    s = report["status"]

    avg_lat_str = f"{m['avg_latency_sec']:.4f} s"
    p95_lat_str = f"{m['p95_latency_sec']:.4f} s"
    cat_acc_str = f"{m['categorization_accuracy_pct']:.1f}%"
    fp_rate_str = f"{m['false_positive_rate_pct']:.1f}%"
    pol_cat_str = f"{m['policy_compliance_rate_pct']:.1f}%"
    anom_det_str = f"{m['anomaly_detection_rate_pct']:.1f}%"

    lat_status = "[PASS]" if s["latency_passed"] else "[FAIL]"
    acc_status = "[PASS]" if s["accuracy_passed"] else "[FAIL]"
    fp_status = "[PASS]" if s["false_positive_passed"] else "[FAIL]"
    pol_status = "[PASS]" if s["policy_compliance_passed"] else "[FAIL]"

    print("================================================================================")
    print("           SMART RECEIPT PARSER AGENT — ACCURACY & PERFORMANCE AUDIT            ")
    print("================================================================================")
    print(f"Sample Size Evaluated : {report['dataset_size']} receipts")
    print(f"Clean Receipts         : {report['clean_receipts']}")
    print(f"Anomalous / Violations : {report['anomalous_receipts']}")
    print("--------------------------------------------------------------------------------")
    print(f"{'Metric':<30} | {'Target':<12} | {'Actual':<15} | {'Status'}")
    print("--------------------------------------------------------------------------------")
    print(f"{'Average Latency':<30} | {'< 2.00 s':<12} | {avg_lat_str:<15} | {lat_status}")
    print(f"{'p95 Processing Latency':<30} | {'< 2.00 s':<12} | {p95_lat_str:<15} | {lat_status}")
    print(f"{'Categorization Accuracy':<30} | {'>= 95.0%':<12} | {cat_acc_str:<15} | {acc_status}")
    print(f"{'False Positive Rate':<30} | {'< 5.0%':<12} | {fp_rate_str:<15} | {fp_status}")
    print(f"{'Policy Violation Catch':<30} | {'100.0%':<12} | {pol_cat_str:<15} | {pol_status}")
    print(f"{'Anomaly Detection Rate':<30} | {'100.0%':<12} | {anom_det_str:<15} | {pol_status}")
    print("================================================================================")
    if s["overall_benchmark_passed"]:
        print(">>> OVERALL STATUS: ALL PRD BENCHMARK TARGETS SATISFIED [PASS] <<<")
    else:
        print(">>> OVERALL STATUS: ONE OR MORE PRD BENCHMARKS FAILED [FAIL] <<<")
    print("================================================================================\n")


if __name__ == "__main__":
    import sys
    report = run_benchmark()
    print_benchmark_table(report)
    with open("benchmark_results.json", "w") as f:
        json.dump(report, f, indent=2)
    sys.exit(0 if report["status"]["overall_benchmark_passed"] else 1)
