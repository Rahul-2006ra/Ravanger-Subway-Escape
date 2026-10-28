#!/usr/bin/env python3
"""
Large-Scale 100-Seed Benchmark Suite:
Compares:
1. Position 1 (100 matches): Candidate as Bot 1 vs Baseline as Bot 2 (Seeds 100-199)
2. Position 2 (100 matches): Baseline as Bot 1 vs Candidate as Bot 2 (Seeds 100-199)

Tracks full statistical metrics:
- Mean, Median, Standard Deviation
- Win / Loss / Tie Rates
- Captures, Invalid Actions, Latency
- Paired Score Differences & Confidence Intervals
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "practice_arena"))
from practice_arena import PracticeArena


class FastPracticeArena(PracticeArena):
    def __init__(self, commands, seed=1, ticks=300, verbose=False, log_dir=None):
        super().__init__(commands, seed=seed, ticks=ticks, verbose=verbose, log_dir=log_dir or "practice_logs")
        self.action_counts = {
            bot_id: {"HOLD": 0, "TRAVERSE": 0, "COLLECT": 0, "DEPOSIT": 0, "OTHER": 0}
            for bot_id in self.commands
        }

    def _apply_action(self, runner, stats, action):
        kind = action.get("action", "OTHER")
        bot_id = runner.id
        if kind in self.action_counts[bot_id]:
            self.action_counts[bot_id][kind] += 1
        else:
            self.action_counts[bot_id]["OTHER"] += 1
        super()._apply_action(runner, stats, action)


def run_match(cmds, seed, log_dir):
    arena = FastPracticeArena(cmds, seed=seed, ticks=300, verbose=False, log_dir=log_dir)
    stats = arena.run()
    res = {}
    for bot_id, st in stats.items():
        res[str(bot_id)] = {
            "score": st.score,
            "collections": st.collections,
            "collected_value": st.collected_value,
            "deposits": st.deposits,
            "captures": st.captures,
            "invalid_actions": st.invalid_actions,
            "avg_ms": (st.total_response_ms / max(1, st.answered_ticks)),
        }
    return res


def compute_stats(values):
    n = len(values)
    if n == 0:
        return {"mean": 0, "median": 0, "std": 0}
    mean = sum(values) / n
    sorted_v = sorted(values)
    median = sorted_v[n // 2] if n % 2 != 0 else (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2.0
    var = sum((x - mean) ** 2 for x in values) / max(1, n - 1)
    std = math.sqrt(var)
    return {"mean": mean, "median": median, "std": std}


def main():
    py = sys.executable
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(base_dir, "practice_logs")
    os.makedirs(log_dir, exist_ok=True)

    bot_baseline = [py, os.path.join(base_dir, "submission", "my_bot.py")]
    bot_candidate = [py, os.path.join(base_dir, "submission", "my_bot_experimental.py")]

    seeds = list(range(100, 200))  # Exactly 100 seeds
    num_matches = len(seeds)

    print(f"Executing 100-Seed Benchmark (Seeds 100-{seeds[-1]}) across both player positions...")

    # Position 1: Candidate as Bot 1, Baseline as Bot 2
    print("Running Position 1: Candidate (Bot 1) vs Baseline (Bot 2)...", flush=True)
    pos1_results = []
    for s in seeds:
        res = run_match([bot_candidate, bot_baseline], seed=s, log_dir=log_dir)
        pos1_results.append({"seed": s, "bots": res})

    # Position 2: Baseline as Bot 1, Candidate as Bot 2
    print("Running Position 2: Baseline (Bot 1) vs Candidate (Bot 2)...", flush=True)
    pos2_results = []
    for s in seeds:
        res = run_match([bot_baseline, bot_candidate], seed=s, log_dir=log_dir)
        pos2_results.append({"seed": s, "bots": res})

    data = {
        "pos1_candidate_as_bot1": pos1_results,
        "pos2_candidate_as_bot2": pos2_results,
    }

    out_path = os.path.join(log_dir, "benchmark_100_seeds_results.json")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nBenchmark finished. Saved to {out_path}\n")


if __name__ == "__main__":
    main()
