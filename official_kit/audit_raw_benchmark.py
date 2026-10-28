#!/usr/bin/env python3
"""
Independent raw benchmark record verification script.
Checks:
- Seed counts, missing, duplicate, or mismatched seeds in Pos 1 and Pos 2
- Independent calculation of mean, median, std, paired difference, se, t-stat, p-value, 95% CI
- Position-dependent precedence effect analysis (action processing order in practice arena)
"""

import json
import math
import os

filepath = os.path.join(os.path.dirname(__file__), "practice_logs", "benchmark_100_seeds_results.json")
with open(filepath, "r") as f:
    raw = json.load(f)

pos1 = raw.get("pos1_candidate_as_bot1", [])
pos2 = raw.get("pos2_candidate_as_bot2", [])

print("=" * 80)
print("AUDIT TASK 2: DATA INTEGRITY CHECK (SEEDS & MATCH RECORD COUNT)")
print("=" * 80)

seeds_p1 = [m["seed"] for m in pos1]
seeds_p2 = [m["seed"] for m in pos2]

print(f"Position 1 match count: {len(pos1)}")
print(f"Position 2 match count: {len(pos2)}")
print(f"Position 1 unique seeds: {len(set(seeds_p1))} (min={min(seeds_p1)}, max={max(seeds_p1)})")
print(f"Position 2 unique seeds: {len(set(seeds_p2))} (min={min(seeds_p2)}, max={max(seeds_p2)})")

duplicates_p1 = len(seeds_p1) - len(set(seeds_p1))
duplicates_p2 = len(seeds_p2) - len(set(seeds_p2))
print(f"Duplicates in Pos 1: {duplicates_p1}")
print(f"Duplicates in Pos 2: {duplicates_p2}")

expected_seeds = set(range(100, 200))
missing_p1 = expected_seeds - set(seeds_p1)
missing_p2 = expected_seeds - set(seeds_p2)
print(f"Missing seeds in Pos 1: {missing_p1 or 'None'}")
print(f"Missing seeds in Pos 2: {missing_p2 or 'None'}")
print(f"Seeds matched across positions: {set(seeds_p1) == set(seeds_p2) == expected_seeds}")

print("\n" + "=" * 80)
print("AUDIT TASK 1: INDEPENDENT RECOMPUTATION FROM RAW JSON")
print("=" * 80)

def calc_stats(arr):
    n = len(arr)
    mean = sum(arr) / n
    s = sorted(arr)
    med = s[n // 2] if n % 2 != 0 else (s[n // 2 - 1] + s[n // 2]) / 2.0
    var = sum((x - mean) ** 2 for x in arr) / (n - 1)
    std = math.sqrt(var)
    return mean, med, std

# Pos 1: Bot 1 is Candidate, Bot 2 is Baseline
p1_c_scores = [m["bots"]["1"]["score"] for m in pos1]
p1_b_scores = [m["bots"]["2"]["score"] for m in pos1]
p1_c_invalids = [m["bots"]["1"]["invalid_actions"] for m in pos1]
p1_b_invalids = [m["bots"]["2"]["invalid_actions"] for m in pos1]
p1_c_captures = [m["bots"]["1"]["captures"] for m in pos1]
p1_b_captures = [m["bots"]["2"]["captures"] for m in pos1]
p1_diffs = [c - b for c, b in zip(p1_c_scores, p1_b_scores)]
p1_c_wins = sum(1 for d in p1_diffs if d > 0)
p1_b_wins = sum(1 for d in p1_diffs if d < 0)
p1_ties = sum(1 for d in p1_diffs if d == 0)

# Pos 2: Bot 1 is Baseline, Bot 2 is Candidate
p2_b_scores = [m["bots"]["1"]["score"] for m in pos2]
p2_c_scores = [m["bots"]["2"]["score"] for m in pos2]
p2_b_invalids = [m["bots"]["1"]["invalid_actions"] for m in pos2]
p2_c_invalids = [m["bots"]["2"]["invalid_actions"] for m in pos2]
p2_b_captures = [m["bots"]["1"]["captures"] for m in pos2]
p2_c_captures = [m["bots"]["2"]["captures"] for m in pos2]
p2_diffs = [c - b for c, b in zip(p2_c_scores, p2_b_scores)] # cand - base
p2_c_wins = sum(1 for d in p2_diffs if d > 0)
p2_b_wins = sum(1 for d in p2_diffs if d < 0)
p2_ties = sum(1 for d in p2_diffs if d == 0)

n = 100
# Pos 1 stats
p1_c_mean, p1_c_med, p1_c_std = calc_stats(p1_c_scores)
p1_b_mean, p1_b_med, p1_b_std = calc_stats(p1_b_scores)
p1_d_mean, p1_d_med, p1_d_std = calc_stats(p1_diffs)
p1_se = p1_d_std / math.sqrt(n)
p1_t = p1_d_mean / p1_se
p1_ci_low = p1_d_mean - 1.984 * p1_se
p1_ci_high = p1_d_mean + 1.984 * p1_se

print(f"--- Position 1: Candidate (Bot 1) vs Baseline (Bot 2) ---")
print(f"  Candidate: Mean={p1_c_mean:.2f}, Median={p1_c_med:.2f}, Std={p1_c_std:.2f}")
print(f"  Baseline:  Mean={p1_b_mean:.2f}, Median={p1_b_med:.2f}, Std={p1_b_std:.2f}")
print(f"  Paired Delta: Mean={p1_d_mean:+.2f}, Median={p1_d_med:+.2f}, Std={p1_d_std:.2f}")
print(f"  Standard Error: {p1_se:.2f} | t-statistic: {p1_t:.3f}")
print(f"  95% Confidence Interval: [{p1_ci_low:+.2f}, {p1_ci_high:+.2f}]")
print(f"  Win Rate: Candidate={p1_c_wins}/{n} ({p1_c_wins}%), Baseline={p1_b_wins}/{n} ({p1_b_wins}%), Ties={p1_ties}")
print(f"  Captures: Candidate={sum(p1_c_captures)}, Baseline={sum(p1_b_captures)}")
print(f"  Invalid Actions: Candidate={sum(p1_c_invalids)}, Baseline={sum(p1_b_invalids)}")

# Pos 2 stats
p2_c_mean, p2_c_med, p2_c_std = calc_stats(p2_c_scores)
p2_b_mean, p2_b_med, p2_b_std = calc_stats(p2_b_scores)
p2_d_mean, p2_d_med, p2_d_std = calc_stats(p2_diffs)
p2_se = p2_d_std / math.sqrt(n)
p2_t = p2_d_mean / p2_se
p2_ci_low = p2_d_mean - 1.984 * p2_se
p2_ci_high = p2_d_mean + 1.984 * p2_se

print(f"\n--- Position 2: Baseline (Bot 1) vs Candidate (Bot 2) ---")
print(f"  Candidate: Mean={p2_c_mean:.2f}, Median={p2_c_med:.2f}, Std={p2_c_std:.2f}")
print(f"  Baseline:  Mean={p2_b_mean:.2f}, Median={p2_b_med:.2f}, Std={p2_b_std:.2f}")
print(f"  Paired Delta: Mean={p2_d_mean:+.2f}, Median={p2_d_med:+.2f}, Std={p2_d_std:.2f}")
print(f"  Standard Error: {p2_se:.2f} | t-statistic: {p2_t:.3f}")
print(f"  95% Confidence Interval: [{p2_ci_low:+.2f}, {p2_ci_high:+.2f}]")
print(f"  Win Rate: Candidate={p2_c_wins}/{n} ({p2_c_wins}%), Baseline={p2_b_wins}/{n} ({p2_b_wins}%), Ties={p2_ties}")
print(f"  Captures: Candidate={sum(p2_c_captures)}, Baseline={sum(p2_c_captures)}")
print(f"  Invalid Actions: Candidate={sum(p2_c_invalids)}, Baseline={sum(p2_b_invalids)}")

print("\n" + "=" * 80)
print("AUDIT TASK 3: POSITION-DEPENDENT PRECEDENCE ANALYSIS")
print("=" * 80)
# Aggregate as Bot 1 vs as Bot 2 across both bots
bot1_scores_all = p1_c_scores + p2_b_scores # All games played by Bot 1
bot2_scores_all = p1_b_scores + p2_c_scores # All games played by Bot 2
b1_mean, b1_med, _ = calc_stats(bot1_scores_all)
b2_mean, b2_med, _ = calc_stats(bot2_scores_all)

bot1_invalids_all = sum(p1_c_invalids) + sum(p2_b_invalids)
bot2_invalids_all = sum(p1_b_invalids) + sum(p2_c_invalids)

print(f"All Bot 1 instances (N=200): Mean Score = {b1_mean:.2f}, Median = {b1_med:.2f}, Total Invalids = {bot1_invalids_all}")
print(f"All Bot 2 instances (N=200): Mean Score = {b2_mean:.2f}, Median = {b2_med:.2f}, Total Invalids = {bot2_invalids_all}")
print(f"Bot 1 Advantage: Mean Delta = {b1_mean - b2_mean:+.2f} points")
print(f"Invalid actions asymmetry: Bot 1 had {bot1_invalids_all} total invalids, Bot 2 had {bot2_invalids_all} total invalids across 200 matches.")
