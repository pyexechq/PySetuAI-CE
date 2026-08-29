"""Benchmark Evaluation and Accuracy Harness for Deterministic Classifier (Zero-AI).

Evaluates CSV/JSONL labeled datasets with sub-millisecond per-row throughput,
computes precision, recall, F1, latency percentiles, and confusion matrices.
"""

from __future__ import annotations

import csv
import io
import json
import os
import time
from collections import defaultdict
from typing import Any, List, Optional


def _percentile(values: list[float], p: float) -> float:
    """Pure Python percentile calculation."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1
    if c < len(sorted_vals):
        return round(sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f]), 1)
    return round(sorted_vals[f], 1)


from app.services.classifier.intent_engine import classify_intent_and_risk


DEFAULT_DATASET_PATHS = [
    "/app/training data/pysetu_intent_risk_training_10000.jsonl",
    "training data/pysetu_intent_risk_training_10000.jsonl",
    "/opt/pysetu/training data/pysetu_intent_risk_training_10000.jsonl",
    "/Volumes/PyExec AI/PyExec Local Repository /PySetuAI/PySetuAI/training data/pysetu_intent_risk_training_10000.jsonl",
]


def load_dataset_rows(file_content: Optional[str] = None, file_format: str = "jsonl") -> list[dict[str, Any]]:
    """Loads dataset rows from uploaded content or default server training dataset."""
    rows: list[dict[str, Any]] = []

    if file_content:
        if file_format == "csv" or ("," in file_content[:100] and "{" not in file_content[:20]):
            reader = csv.DictReader(io.StringIO(file_content))
            for r in reader:
                rows.append(dict(r))
        else:
            for line in file_content.splitlines():
                if line.strip():
                    try:
                        rows.append(json.loads(line.strip()))
                    except Exception:
                        pass
        return rows

    # Fallback to server dataset path
    for p in DEFAULT_DATASET_PATHS:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            rows.append(json.loads(line.strip()))
                        except Exception:
                            pass
            if rows:
                break

    return rows


async def execute_dataset_benchmark(
    file_content: Optional[str] = None,
    file_format: str = "jsonl",
    sample_limit: Optional[int] = None,
) -> dict[str, Any]:
    """
    Executes high-speed deterministic evaluation across the dataset.
    Returns complete precision, recall, latency distribution, confusion matrix, and scenario breakdown.
    """
    rows = load_dataset_rows(file_content, file_format)
    if sample_limit and sample_limit > 0:
        rows = rows[:sample_limit]

    if not rows:
        raise ValueError("No dataset rows found to benchmark.")

    latencies_micros: list[float] = []
    tp = 0  # Expected threat, detected harm
    tn = 0  # Expected allow, allowed
    fp = 0  # Expected allow, detected harm
    fn = 0  # Expected threat, allowed

    scenario_breakdown: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"total": 0, "correct": 0, "missed": 0, "expected_decision": "", "risk_level": ""}
    )
    missed_samples: list[dict[str, Any]] = []

    start_total = time.perf_counter()

    for row in rows:
        text = str(row.get("text") or row.get("prompt") or "")
        expected_decision = str(row.get("decision") or "allow").lower().strip()
        reason_code = str(row.get("reason_code") or row.get("scenario") or "GENERAL")
        risk_level = str(row.get("risk_level") or "medium").lower()

        verdict = await classify_intent_and_risk(db=None, text=text)
        latencies_micros.append(verdict.execution_time_micros)

        is_expected_harm = expected_decision in ("block_alert", "block", "require_approval", "redact", "warn")
        is_detected_harm = verdict.verdict in ("block", "request_approval", "redact", "monitor")

        s_entry = scenario_breakdown[reason_code]
        s_entry["total"] += 1
        s_entry["expected_decision"] = expected_decision
        s_entry["risk_level"] = risk_level

        if is_expected_harm and is_detected_harm:
            tp += 1
            s_entry["correct"] += 1
        elif not is_expected_harm and not is_detected_harm:
            tn += 1
            s_entry["correct"] += 1
        elif not is_expected_harm and is_detected_harm:
            fp += 1
            s_entry["missed"] += 1
        else:
            fn += 1
            s_entry["missed"] += 1
            if len(missed_samples) < 20:
                missed_samples.append({
                    "id": row.get("id"),
                    "text": text,
                    "expected": expected_decision,
                    "reason_code": reason_code,
                    "got_verdict": verdict.verdict,
                })

    total_time_ms = round((time.perf_counter() - start_total) * 1000.0, 2)
    total_count = len(rows)
    accuracy = round(((tp + tn) / total_count) * 100.0, 2) if total_count > 0 else 0.0
    precision = round((tp / (tp + fp)) * 100.0, 2) if (tp + fp) > 0 else 0.0
    recall = round((tp / (tp + fn)) * 100.0, 2) if (tp + fn) > 0 else 0.0
    f1 = round((2 * precision * recall) / (precision + recall), 2) if (precision + recall) > 0 else 0.0
    fpr = round((fp / (fp + tn)) * 100.0, 2) if (fp + tn) > 0 else 0.0

    avg_lat = round(sum(latencies_micros) / len(latencies_micros), 1) if latencies_micros else 0.0
    p50_lat = _percentile(latencies_micros, 50)
    p95_lat = _percentile(latencies_micros, 95)
    p99_lat = _percentile(latencies_micros, 99)

    # Format scenario table
    scenarios_out = []
    for sc, d in sorted(scenario_breakdown.items(), key=lambda x: x[1]["total"], reverse=True):
        acc = round((d["correct"] / d["total"]) * 100.0, 1) if d["total"] > 0 else 0.0
        scenarios_out.append({
            "scenario": sc,
            "total_rows": d["total"],
            "accuracy_percent": acc,
            "expected_decision": d["expected_decision"],
            "risk_level": d["risk_level"],
            "status": "PASS" if acc >= 90.0 else "REVIEW",
        })

    return {
        "total_rows_evaluated": total_count,
        "total_time_ms": total_time_ms,
        "scan_rate_per_sec": round((total_count / (total_time_ms / 1000.0)), 0) if total_time_ms > 0 else 0,
        "accuracy_percent": accuracy,
        "precision_percent": precision,
        "recall_percent": recall,
        "f1_score_percent": f1,
        "false_positive_rate_percent": fpr,
        "latency_profile": {
            "avg_micros": avg_lat,
            "avg_ms": round(avg_lat / 1000.0, 4),
            "p50_micros": p50_lat,
            "p95_micros": p95_lat,
            "p99_micros": p99_lat,
        },
        "confusion_matrix": {
            "true_positives": tp,
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
        },
        "scenario_breakdown": scenarios_out,
        "missed_samples": missed_samples,
    }
