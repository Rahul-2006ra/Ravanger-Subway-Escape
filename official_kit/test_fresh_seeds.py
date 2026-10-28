#!/usr/bin/env python3
"""
Targeted validation script running Candidate vs Baseline on FRESH seeds (200-249).
Runs 50 matches per position (100 total matches).
Computes:
- Mean and Median scores
- Win rates
- Captures
- Invalid actions breakdown
- Paired score differences and 95% Confidence Intervals
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "practice_arena"))
from practice_arena import PracticeArena

def run_match(cmds, seed):
    arena = PracticeArena(cmds, seed=seed, ticks=300, verbose=False, log_dir="practice_logs")
    stats = arena.run()
    res = {}
    for bot_id, st in stats.items():
        res[str(bot_id)] = {
            "score": st.score,
            "collections": st.collections,
            "deposits": st.deposits,
            "captures": st.captures,
            "invalid_actions": st.invalid_actions,
            "avg_ms": (st.total_response_ms / max(1, st.answered_ticks)),
        }
    return res

def stats_summary(arr):
    n = len(arr)
    mean = sum(arr) / n
    sorted_arr = sorted(arr)
    median = sorted_arr[n // 2] if n % 2 != 0 else (sorted_arr[n // 2 - 1] + sorted_arr[n // 2]) / 2.0
    var = sum((x - mean) ** 2 for x in arr) / max(1, n - 1)
    std = math.sqrt(var)
    return mean, median, std

def main():
    py = sys.executable
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bot_baseline = [py, os.path.join(base_dir, "submission", "my_bot.py")]
    bot_candidate = [py, os.path.join(base_dir, "submission", "my_bot_experimental.py")]

    new_seeds = list(range(200, 250)) # 50 fresh seeds
    n = len(new_seeds)

    print(f"Running fresh validation on {n} unseen seeds (200-{new_seeds[-1]})...", flush=True)

    # Position 1: Candidate as Bot 1, Baseline as Bot 2
    pos1_matches = []
    for s in new_seeds:
        res = run_match([bot_candidate, bot_baseline], seed=s)
        pos1_matches.append({"seed": s, "bots": res})

    # Position 2: Baseline as Bot 1, Candidate as Bot 2
    pos2_matches = []
    for s in new_seeds:
        res = run_match([bot_baseline, bot_candidate], seed=s)
        pos2_matches.append({"seed": s, "bots": res})

    def analyze_pos(name, matches, cand_is_bot1=True):
        c_scores, b_scores = [], []
        c_caps, b_caps = [], []
        c_invs, b_invs = [], []
        c_wins, b_wins, ties = 0, 0, 0
        diffs = []

        for m in matches:
            b1 = m["bots"]["1"]
            b2 = m["bots"]["2"]
            c = b1 if cand_is_bot1 else b2
            b = b2 if cand_is_bot1 else b1

            c_scores.append(c["score"])
            b_scores.append(b["score"])
            c_caps.append(c["captures"])
            b_caps.append(b["captures"])
            c_invs.append(c["invalid_actions"])
            b_invs.append(b["invalid_actions"])

            delta = c["score"] - b["score"]
            diffs.append(delta)
            if delta > 0:
                c_wins += 1
            elif delta < 0:
                b_wins += 1
            else:
                ties += 1

        c_mean, c_med, c_std = stats_summary(c_scores)
        b_mean, b_med, b_std = stats_summary(b_scores)
        d_mean, d_med, d_std = stats_summary(diffs)
        se = d_std / math.sqrt(n)
        ci_low = d_mean - 2.01 * se
        ci_high = d_mean + 2.01 * se

        print("=" * 80)
        print(f"{name} (N = {n} Fresh Seeds 200-{200+n-1})")
        print("=" * 80)
        print(f"Candidate: Mean={c_mean:.2f}, Median={c_med:.2f}, Std={c_std:.2f}")
        print(f"Baseline:  Mean={b_mean:.2f}, Median={b_med:.2f}, Std={b_std:.2f}")
        print(f"Paired Difference (Candidate - Baseline):")
        print(f"  Mean Delta:   {d_mean:+.2f} points (SE = {se:.2f})")
        print(f"  Median Delta: {d_med:+.2f} points")
        print(f"  95% CI:       [{ci_low:+.2f}, {ci_high:+.2f}]")
        print(f"Win Rate:  Candidate={c_wins}/{n} ({c_wins/n*100:.1f}%), Baseline={b_wins}/{n} ({b_wins/n*100:.1f}%), Ties={ties}")
        print(f"Captures:  Candidate={sum(c_caps)} ({sum(c_caps)/n:.2f}/match), Baseline={sum(b_caps)} ({sum(b_caps)/n:.2f}/match)")
        print(f"Invalids:  Candidate={sum(c_invs)} ({sum(c_invs)/n:.2f}/match), Baseline={sum(b_invs)} ({sum(b_invs)/n:.2f}/match)")
        return c_mean, b_mean, c_wins, b_wins, d_mean

    p1_cm, p1_bm, p1_cw, p1_bw, p1_delta = analyze_pos("POSITION 1: Candidate (Bot 1) vs Baseline (Bot 2)", pos1_matches, cand_is_bot1=True)
    p2_cm, p2_bm, p2_cw, p2_bw, p2_delta = analyze_pos("POSITION 2: Baseline (Bot 1) vs Candidate (Bot 2)", pos2_matches, cand_is_bot1=False)

    print("\n" + "=" * 80)
    print("FRESH SEEDS OVERALL AGGREGATE (100 MATCHES)")
    print("=" * 80)
    cand_overall = (p1_cm + p2_cm) / 2.0
    base_overall = (p1_bm + p2_bm) / 2.0
    print(f"Candidate Overall Mean Score: {cand_overall:.2f}")
    print(f"Baseline Overall Mean Score:  {base_overall:.2f}")
    print(f"Candidate Overall Net Delta:  {cand_overall - base_overall:+.2f} points")
    print(f"Candidate Total Wins:         {p1_cw + p2_cw} / 100 ({(p1_cw + p2_cw)}%)")
    print(f"Baseline Total Wins:          {p1_bw + p2_bw} / 100 ({(p1_bw + p2_bw)}%)")

if __name__ == "__main__":
    main()
