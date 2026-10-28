#!/usr/bin/env python3
import json
import os

filepath = os.path.join(os.path.dirname(__file__), "practice_logs", "benchmark_experimental_results.json")
with open(filepath, "r") as f:
    data = json.load(f)

print("=" * 80)
print("BENCHMARK ANALYSIS: EXPERIMENTAL CANDIDATE (Safehouse Decoupling) VS BASELINE")
print("=" * 80)

def summarize_config(name, cfg_data, bot1_name, bot2_name=None):
    b1_scores = []
    b2_scores = []
    b1_captures = []
    b1_invalids = []
    b1_collections = []
    b1_deposits = []
    b1_ms = []
    b1_wins = 0
    ties = 0

    for match in cfg_data:
        bots = match["bots"]
        s1 = bots["1"]["score"]
        b1_scores.append(s1)
        b1_captures.append(bots["1"]["captures"])
        b1_invalids.append(bots["1"]["invalid_actions"])
        b1_collections.append(bots["1"]["collections"])
        b1_deposits.append(bots["1"]["deposits"])
        b1_ms.append(bots["1"]["avg_ms"])

        if "2" in bots:
            s2 = bots["2"]["score"]
            b2_scores.append(s2)
            if s1 > s2:
                b1_wins += 1
            elif s1 == s2:
                ties += 1

    n = len(cfg_data)
    avg_s1 = sum(b1_scores) / n
    avg_caps = sum(b1_captures) / n
    avg_inv = sum(b1_invalids) / n
    avg_col = sum(b1_collections) / n
    avg_dep = sum(b1_deposits) / n
    avg_resp = sum(b1_ms) / n

    if bot2_name:
        avg_s2 = sum(b2_scores) / n
        win_rate = (b1_wins / n) * 100
        print(f"[{name}] (N={n})")
        print(f"  Bot 1 ({bot1_name}): Avg Score = {avg_s1:.2f} | Win Rate = {win_rate:.1f}% ({b1_wins}/{n}) | Captures = {avg_caps:.2f} | Invalids = {avg_inv:.2f} | Resp = {avg_resp:.2f}ms")
        print(f"  Bot 2 ({bot2_name}): Avg Score = {avg_s2:.2f}")
    else:
        print(f"[{name}] (N={n})")
        print(f"  {bot1_name} Solo: Avg Score = {avg_s1:.2f} | Captures = {avg_caps:.2f} | Invalids = {avg_inv:.2f} | Collections = {avg_col:.1f} | Deposits = {avg_dep:.1f} | Resp = {avg_resp:.2f}ms")
    print("-" * 80)

summarize_config("Candidate vs Basic", data["exp_vs_basic"], "Experimental", "BasicBot")
summarize_config("Baseline vs Basic", data["baseline_vs_basic"], "Baseline (my_bot)", "BasicBot")
print()
summarize_config("Basic vs Candidate", data["basic_vs_exp"], "BasicBot", "Experimental")
summarize_config("Basic vs Baseline", data["basic_vs_baseline"], "BasicBot", "Baseline (my_bot)")
print()
summarize_config("Candidate Solo", data["exp_solo"], "Experimental")
summarize_config("Baseline Solo", data["baseline_solo"], "Baseline (my_bot)")
print()
summarize_config("HEAD-TO-HEAD: Candidate as Bot 1 vs Baseline as Bot 2", data["exp_vs_baseline"], "Experimental", "Baseline (my_bot)")
summarize_config("HEAD-TO-HEAD: Baseline as Bot 1 vs Candidate as Bot 2", data["baseline_vs_exp"], "Baseline (my_bot)", "Experimental")
