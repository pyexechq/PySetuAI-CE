"""Full 10,000-Row Evaluation and Latency Benchmark Harness."""

import asyncio
import json
import time
from collections import defaultdict
import numpy as np

from app.services.classifier.intent_engine import classify_intent_and_risk


async def run_benchmark():
    dataset_path = "training data/pysetu_intent_risk_training_10000.jsonl"
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = [json.loads(line) for line in f if line.strip()]

    print(f"Loaded {len(data)} rows for evaluation benchmark.")

    latencies_micros = []
    tp = 0  # Expected block/approval/redact, Got non-allow
    tn = 0  # Expected allow, Got allow
    fp = 0  # Expected allow, Got block/approval/redact
    fn = 0  # Expected block/approval/redact, Got allow

    category_stats = defaultdict(lambda: {"total": 0, "correct": 0, "missed": 0})
    missed_samples = []

    start_total = time.perf_counter()

    for idx, row in enumerate(data):
        text = row.get("text", "")
        expected_decision = row.get("decision", "allow")
        reason_code = row.get("reason_code", "UNKNOWN")

        verdict = await classify_intent_and_risk(db=None, text=text)
        latencies_micros.append(verdict.execution_time_micros)

        is_expected_harm = expected_decision in ("block_alert", "block", "require_approval", "redact", "warn")
        is_detected_harm = verdict.verdict in ("block", "request_approval", "redact", "monitor")

        category_stats[reason_code]["total"] += 1

        if is_expected_harm and is_detected_harm:
            tp += 1
            category_stats[reason_code]["correct"] += 1
        elif not is_expected_harm and not is_detected_harm:
            tn += 1
            category_stats[reason_code]["correct"] += 1
        elif not is_expected_harm and is_detected_harm:
            fp += 1
            category_stats[reason_code]["missed"] += 1
        else:
            fn += 1
            category_stats[reason_code]["missed"] += 1
            if len(missed_samples) < 15:
                missed_samples.append({
                    "id": row.get("id"),
                    "text": text,
                    "expected": expected_decision,
                    "reason_code": reason_code,
                    "got_verdict": verdict.verdict,
                })

    total_time_ms = (time.perf_counter() - start_total) * 1000.0
    accuracy = (tp + tn) / len(data) * 100.0
    precision = tp / (tp + fp) * 100.0 if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) * 100.0 if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) * 100.0 if (fp + tn) > 0 else 0.0

    print("\n=======================================================")
    print(" 🚀 PYSETU CLASSIFIER 10,000-ROW BENCHMARK RESULTS")
    print("=======================================================")
    print(f" Total Rows Evaluated: {len(data):,}")
    print(f" Total Benchmark Time: {total_time_ms:.2f} ms ({total_time_ms/len(data):.3f} ms / scan)")
    print(f"\n 📊 Accuracy: {accuracy:.2f}%")
    print(f" 🎯 Precision: {precision:.2f}%")
    print(f" 🔍 Recall:    {recall:.2f}%")
    print(f" ⭐ F1-Score:  {f1:.2f}%")
    print(f" 🛡️ False Positive Rate (FPR): {fpr:.2f}%")
    print(f"\n ⚡ Latency Profile (Zero-AI Deterministic Execution):")
    print(f"    - Average: {np.mean(latencies_micros):.1f} μs ({np.mean(latencies_micros)/1000.0:.3f} ms)")
    print(f"    - p50:     {np.percentile(latencies_micros, 50):.1f} μs")
    print(f"    - p95:     {np.percentile(latencies_micros, 95):.1f} μs")
    print(f"    - p99:     {np.percentile(latencies_micros, 99):.1f} μs")
    print("\n 📦 Confusion Matrix:")
    print(f"    - True Positives (Harm Blocked/Intercepted): {tp:,}")
    print(f"    - True Negatives (Benign Allowed):           {tn:,}")
    print(f"    - False Positives (Falsely Intercepted):     {fp:,}")
    print(f"    - False Negatives (Missed Threat Rows):      {fn:,}")

    if missed_samples:
        print("\n ⚠️ Sample Missed Edge Cases:")
        for m in missed_samples[:5]:
            print(f"    [{m['reason_code']}] '{m['text']}' -> got {m['got_verdict']} (expected {m['expected']})")

    print("=======================================================\n")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "backend")
    asyncio.run(run_benchmark())
