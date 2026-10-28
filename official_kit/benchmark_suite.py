#!/usr/bin/env python3
"""
Comprehensive Benchmarking Suite for Subway Escape Bot.
Compares:
1. my_bot.py (New Opponent-Aware) vs basic_bot.py
2. basic_bot.py vs my_bot.py (Reversed)
3. my_bot.py Solo
4. my_bot_safety.py Solo
5. my_bot_safety.py vs basic_bot.py
6. basic_bot.py vs my_bot_safety.py

Runs across seeds 100-109 twice to verify 100% determinism and reproducibility.
Tracks action distributions (HOLD, TRAVERSE, COLLECT, DEPOSIT) to observe HOLD reduction on seeds 108/109.
"""

import json
import os
import sys
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "practice_arena"))
from practice_arena import PracticeArena, BotStats


class InstrumentedPracticeArena(PracticeArena):
    def __init__(self, commands, seed=1, ticks=300, verbose=False, log_dir="practice_logs"):
        super().__init__(commands, seed=seed, ticks=ticks, verbose=verbose, log_dir=log_dir)
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


def run_single_match(bot_cmds, seed, log_dir="practice_logs"):
    arena = InstrumentedPracticeArena(bot_cmds, seed=seed, ticks=300, verbose=False, log_dir=log_dir)
    stats = arena.run()
    result = {}
    for bot_id, st in stats.items():
        result[str(bot_id)] = {
            "score": st.score,
            "collections": st.collections,
            "collected_value": st.collected_value,
            "deposits": st.deposits,
            "captures": st.captures,
            "loot_lost": st.loot_lost,
            "invalid_actions": st.invalid_actions,
            "misses": st.misses,
            "disqualified": st.disqualified,
            "avg_ms": (st.total_response_ms / max(1, st.answered_ticks)),
            "max_ms": st.max_response_ms,
            "actions": arena.action_counts[bot_id],
        }
    return result


def main():
    py = sys.executable
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(base_dir, "practice_logs")
    os.makedirs(log_dir, exist_ok=True)

    my_bot = [py, os.path.join(base_dir, "submission", "my_bot.py")]
    my_bot_safety = [py, os.path.join(base_dir, "submission", "my_bot_safety.py")]
    basic_bot = [py, os.path.join(base_dir, "sample_bot", "python", "basic_bot.py")]

    configs = {
        "new_vs_basic": [my_bot, basic_bot],
        "basic_vs_new": [basic_bot, my_bot],
        "new_solo": [my_bot],
        "safety_solo": [my_bot_safety],
        "safety_vs_basic": [my_bot_safety, basic_bot],
        "basic_vs_safety": [basic_bot, my_bot_safety],
    }

    seeds = list(range(100, 110))
    all_runs = {}

    for run_iter in (1, 2):
        print(f"============================================================")
        print(f" STARTING BENCHMARK ITERATION {run_iter} (Seeds 100-109)")
        print(f"============================================================")
        run_data = {}
        for cfg_name, cmds in configs.items():
            print(f"Running config: {cfg_name} ...", flush=True)
            cfg_matches = []
            for seed in seeds:
                res = run_single_match(cmds, seed=seed, log_dir=log_dir)
                cfg_matches.append({"seed": seed, "bots": res})
            run_data[cfg_name] = cfg_matches
        all_runs[f"iteration_{run_iter}"] = run_data

    # Check reproducibility
    print("\nVerifying 100% determinism between iteration 1 and iteration 2...")
    diff_count = 0
    iter1 = all_runs["iteration_1"]
    iter2 = all_runs["iteration_2"]
    for cfg in configs:
        for m1, m2 in zip(iter1[cfg], iter2[cfg]):
            seed = m1["seed"]
            for b in m1["bots"]:
                b1 = m1["bots"][b]
                b2 = m2["bots"][b]
                if (b1["score"] != b2["score"] or 
                    b1["collections"] != b2["collections"] or 
                    b1["deposits"] != b2["deposits"] or 
                    b1["captures"] != b2["captures"] or 
                    b1["actions"] != b2["actions"]):
                    print(f"DIFF at {cfg} seed {seed} bot {b}: score1={b1['score']} score2={b2['score']}")
                    diff_count += 1

    if diff_count == 0:
        print("[PASS] Benchmark is 100% deterministic and reproducible across all seeds and configurations!")
    else:
        print(f"[FAIL] Found {diff_count} discrepancies between benchmark runs!")

    out_file = os.path.join(log_dir, "opponent_aware_benchmark.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_runs, f, indent=2)
    print(f"Saved benchmark results to {out_file}")


if __name__ == "__main__":
    main()
