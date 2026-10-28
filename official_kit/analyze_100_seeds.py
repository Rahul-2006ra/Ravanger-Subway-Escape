#!/usr/bin/env python3
"""
Comprehensive Statistical Analysis for 100-Seed Benchmark:
- Position 1 (N=100): Candidate (Bot 1) vs Baseline (Bot 2)
- Position 2 (N=100): Baseline (Bot 1) vs Candidate (Bot 2)
Computes:
- Means, Medians, Std Devs
- Win / Tie / Loss counts & percentages
- Captures, Invalids, Response Latency
- Paired difference distribution, standard error, t-stat, p-value, 95% CI
"""

import json
import math
import os

filepath = os.path.join(os.path.dirname(__file__), "practice_logs", "benchmark_100_seeds_results.json")
with open(filepath, "r") as f:
    data = json.load(f)

def stats_summary(arr):
    n = len(arr)
    mean = sum(arr) / n
    sorted_arr = sorted(arr)
    median = sorted_arr[n // 2] if n % 2 != 0 else (sorted_arr[n // 2 - 1] + sorted_arr[n // 2]) / 2.0
    var = sum((x - mean) ** 2 for x in arr) / max(1, n - 1)
    std = math.sqrt(var)
    return mean, median, std

def analyze_position(pos_name, matches, cand_is_bot1=True):
    n = len(matches)
    cand_scores = []
    base_scores = []
    cand_caps = []
    base_caps = []
    cand_inv = []
    base_inv = []
    cand_ms = []
    base_ms = []
    diffs = [] # cand - base

    cand_wins = 0
    base_wins = 0
    ties = 0

    for m in matches:
        b1 = m["bots"]["1"]
        b2 = m["bots"]["2"]
        if cand_is_bot1:
            c_score, b_score = b1["score"], b2["score"]
            c_cap, b_cap = b1["captures"], b2["captures"]
            c_i, b_i = b1["invalid_actions"], b2["invalid_actions"]
            c_lat, b_lat = b1["avg_ms"], b2["avg_ms"]
        else:
            b_score, c_score = b1["score"], b2["score"]
            b_cap, c_cap = b1["captures"], b2["captures"]
            b_i, c_i = b1["invalid_actions"], b2["invalid_actions"]
            b_lat, c_lat = b1["avg_ms"], b2["avg_ms"]

        cand_scores.append(c_score)
        base_scores.append(b_score)
        cand_caps.append(c_cap)
        base_caps.append(b_cap)
        cand_inv.append(c_i)
        base_inv.append(b_i)
        cand_ms.append(c_lat)
        base_ms.append(b_lat)
        diff = c_score - b_score
        diffs.append(diff)

        if c_score > b_score:
            cand_wins += 1
        elif b_score > c_score:
            base_wins += 1
        else:
            ties += 1

    c_mean, c_med, c_std = stats_summary(cand_scores)
    b_mean, b_med, b_std = stats_summary(base_scores)
    diff_mean, diff_med, diff_std = stats_summary(diffs)

    # Paired t-test
    se_diff = diff_std / math.sqrt(n)
    t_stat = diff_mean / se_diff if se_diff > 0 else 0.0
    ci_95_low = diff_mean - 1.984 * se_diff
    ci_95_high = diff_mean + 1.984 * se_diff

    print("=" * 80)
    print(f"POSITION: {pos_name} (N = {n} matches, Seeds 100-{100 + n - 1})")
    print("=" * 80)
    print(f"Candidate ({'Bot 1' if cand_is_bot1 else 'Bot 2'}):")
    print(f"  Mean Score:   {c_mean:.2f} (Std: {c_std:.2f})")
    print(f"  Median Score: {c_med:.2f}")
    print(f"  Win Rate:     {cand_wins}/{n} ({cand_wins/n*100:.1f}%) | Losses: {base_wins}/{n} | Ties: {ties}/{n}")
    print(f"  Avg Captures: {sum(cand_caps)/n:.3f} | Total: {sum(cand_caps)}")
    print(f"  Avg Invalids: {sum(cand_inv)/n:.3f} | Total: {sum(cand_inv)}")
    print(f"  Avg Latency:  {sum(cand_ms)/n:.2f} ms")
    print()
    print(f"Baseline ({'Bot 2' if cand_is_bot1 else 'Bot 1'}):")
    print(f"  Mean Score:   {b_mean:.2f} (Std: {b_std:.2f})")
    print(f"  Median Score: {b_med:.2f}")
    print(f"  Avg Captures: {sum(base_caps)/n:.3f} | Total: {sum(base_caps)}")
    print(f"  Avg Invalids: {sum(base_inv)/n:.3f} | Total: {sum(base_inv)}")
    print(f"  Avg Latency:  {sum(base_ms)/n:.2f} ms")
    print()
    print(f"Paired Difference (Candidate - Baseline):")
    print(f"  Mean Delta:   {diff_mean:+.2f} points")
    print(f"  Median Delta: {diff_med:+.2f} points")
    print(f"  Std Error:    {se_diff:.2f}")
    print(f"  95% CI:       [{ci_95_low:+.2f}, {ci_95_high:+.2f}]")
    print(f"  t-statistic:  {t_stat:.3f}")
    print()
    return {
        "c_mean": c_mean, "c_med": c_med, "b_mean": b_mean, "b_med": b_med,
        "cand_wins": cand_wins, "base_wins": base_wins, "ties": ties,
        "diff_mean": diff_mean, "diff_med": diff_med, "t_stat": t_stat,
        "ci_95": (ci_95_low, ci_95_high), "n": n
    }

p1 = analyze_position("Position 1: Candidate as Bot 1 vs Baseline as Bot 2", data["pos1_candidate_as_bot1"], cand_is_bot1=True)
p2 = analyze_position("Position 2: Baseline as Bot 1 vs Candidate as Bot 2", data["pos2_candidate_as_bot2"], cand_is_bot1=False)

print("=" * 80)
print("AGGREGATE OVERALL HEAD-TO-HEAD (200 TOTAL MATCHES)")
print("=" * 80)
overall_cand_avg = (p1["c_mean"] + p2["c_mean"]) / 2.0
overall_base_avg = (p1["b_mean"] + p2["b_mean"]) / 2.0
overall_diff = overall_cand_avg - overall_base_avg
total_cand_wins = p1["cand_wins"] + p2["cand_wins"]
total_base_wins = p1["base_wins"] + p2["base_wins"]
total_ties = p1["ties"] + p2["ties"]

print(f"Candidate Overall Average Score: {overall_cand_avg:.2f}")
print(f"Baseline Overall Average Score:  {overall_base_avg:.2f}")
print(f"Overall Net Advantage:           {overall_diff:+.2f} points")
print(f"Overall Match Wins:              {total_cand_wins}/200 ({total_cand_wins/2:.1f}%) | Baseline Wins: {total_base_wins}/200 ({total_base_wins/2:.1f}%)")
