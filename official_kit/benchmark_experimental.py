#!/usr/bin/env python3
"""
Benchmark comparison script between:
- Primary Bot: official_kit/submission/my_bot.py
- Experimental Candidate Bot: official_kit/submission/my_bot_experimental.py
- Basic Bot: official_kit/sample_bot/python/basic_bot.py

Runs across seeds 100-109 with complete metric tracking.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "practice_arena"))
from practice_arena import PracticeArena


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
    my_exp = [py, os.path.join(base_dir, "submission", "my_bot_experimental.py")]
    basic_bot = [py, os.path.join(base_dir, "sample_bot", "python", "basic_bot.py")]

    configs = {
        "exp_vs_basic": [my_exp, basic_bot],
        "basic_vs_exp": [basic_bot, my_exp],
        "exp_solo": [my_exp],
        "baseline_vs_basic": [my_bot, basic_bot],
        "basic_vs_baseline": [basic_bot, my_bot],
        "baseline_solo": [my_bot],
        "exp_vs_baseline": [my_exp, my_bot],
        "baseline_vs_exp": [my_bot, my_exp],
    }

    seeds = list(range(100, 110))
    benchmark_data = {}

    for cfg_name, cmds in configs.items():
        print(f"Running config: {cfg_name} (Seeds 100-109)...", flush=True)
        cfg_matches = []
        for seed in seeds:
            res = run_single_match(cmds, seed=seed, log_dir=log_dir)
            cfg_matches.append({"seed": seed, "bots": res})
        benchmark_data[cfg_name] = cfg_matches

    out_file = os.path.join(log_dir, "benchmark_experimental_results.json")
    with open(out_file, "w") as f:
        json.dump(benchmark_data, f, indent=2)
    print(f"Benchmark results successfully saved to {out_file}")


if __name__ == "__main__":
    main()
