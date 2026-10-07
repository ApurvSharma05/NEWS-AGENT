#!/usr/bin/env python3
"""
Evaluation Runner for EPC News Filtering and Entity Detection.

Evaluates the NewsFilter against a labeled ground-truth golden dataset:
  - Entity Detection Precision, Recall, and F1 Score
  - Accuracy and Specificity on negative/adversarial distractors
  - Per-company performance breakdown
  - Latency benchmarks
Outputs evaluation metrics to eval/results.json and prints a structured markdown table.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from tools.filter_news import NewsFilter

logging.basicConfig(level=logging.WARNING)


def run_evaluation(golden_path: str = "eval/golden_dataset.json", results_path: str = "eval/results.json") -> dict:
    golden_file = ROOT_DIR / golden_path
    if not golden_file.exists():
        raise FileNotFoundError(f"Golden dataset not found at {golden_file}")

    with open(golden_file, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    news_filter = NewsFilter()

    total_samples = len(dataset)
    tp = 0  # Relevant and predicted relevant
    fp = 0  # Not relevant but predicted relevant (false alarm)
    fn = 0  # Relevant but missed (false negative)
    tn = 0  # Not relevant and correctly rejected

    entity_matches_exact = 0
    entity_matches_total = 0

    company_stats: dict[str, dict[str, int]] = {}

    start_time = time.perf_counter()

    for item in dataset:
        expected_relevant = item.get("relevant", 0) == 1
        expected_companies = set(item.get("expected_companies", []))

        # Run filter
        sample_input = [{
            "title": item.get("title", ""),
            "summary": item.get("summary", ""),
            "link": item.get("link", "https://example.com/test"),
        }]

        filtered = news_filter.filter_articles(sample_input)
        predicted_relevant = len(filtered) > 0
        predicted_companies = set(filtered[0].get("companies", [])) if predicted_relevant else set()

        if predicted_relevant and expected_relevant:
            tp += 1
        elif predicted_relevant and not expected_relevant:
            fp += 1
        elif not predicted_relevant and expected_relevant:
            fn += 1
        else:
            tn += 1

        # Track entity attribution accuracy
        if expected_relevant:
            entity_matches_total += 1
            if expected_companies.issubset(predicted_companies):
                entity_matches_exact += 1

            for comp in expected_companies:
                if comp not in company_stats:
                    company_stats[comp] = {"expected": 0, "detected": 0}
                company_stats[comp]["expected"] += 1
                if comp in predicted_companies:
                    company_stats[comp]["detected"] += 1

    elapsed_sec = time.perf_counter() - start_time
    latency_ms_per_article = (elapsed_sec / total_samples) * 1000

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / total_samples if total_samples > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    entity_accuracy = entity_matches_exact / entity_matches_total if entity_matches_total > 0 else 0.0

    results = {
        "dataset_size": total_samples,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "specificity": round(specificity, 4),
        "entity_detection_accuracy": round(entity_accuracy, 4),
        "latency_ms_per_article": round(latency_ms_per_article, 3),
        "throughput_articles_per_sec": round(total_samples / elapsed_sec, 1) if elapsed_sec > 0 else 0,
        "company_recall": {
            comp: round(data["detected"] / data["expected"], 4) if data["expected"] > 0 else 1.0
            for comp, data in company_stats.items()
        },
    }

    # Save to json
    out_file = ROOT_DIR / results_path
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Print summary report
    print("\n" + "=" * 65)
    print(" EPC Competitor Intelligence — Evaluation Results")
    print("=" * 65)
    print(f" Dataset Size:                {total_samples} articles")
    print(f" Precision:                   {precision:.2%}")
    print(f" Recall:                      {recall:.2%}")
    print(f" F1-Score:                    {f1:.2%}")
    print(f" Accuracy:                    {accuracy:.2%}")
    print(f" Specificity (False Alarm):   {specificity:.2%}")
    print(f" Entity Matching Accuracy:    {entity_accuracy:.2%}")
    print(f" Throughput:                  {results['throughput_articles_per_sec']} articles/sec")
    print(f" Latency:                     {latency_ms_per_article:.3f} ms / article")
    print("=" * 65)
    print(" Per-Company Recall Breakdown:")
    for comp, rec in sorted(results["company_recall"].items()):
        print(f"   - {comp:22s}: {rec:.1%}")
    print("=" * 65 + "\n")

    return results


if __name__ == "__main__":
    run_evaluation()
