import json
import os

with open("practice_logs/opponent_aware_benchmark.json", "r", encoding="utf-8") as f:
    full_data = json.load(f)

iter1 = full_data["iteration_1"]
iter2 = full_data["iteration_2"]

print("=== CHECKING CAPTURES AND LOOT LOST ACROSS ALL CONFIGS (ITERATION 1 & 2) ===")
for it_name, it_data in [("iteration_1", iter1), ("iteration_2", iter2)]:
    for cfg_name, matches in it_data.items():
        for m in matches:
            seed = m["seed"]
            for b_id, st in m["bots"].items():
                if st["captures"] > 0 or st["loot_lost"] > 0:
                    print(f"[{it_name}] {cfg_name} Seed {seed} Bot {b_id}: captures={st['captures']}, loot_lost={st['loot_lost']}")

print("\n=== RECOMPUTING ALL METRICS DIRECTLY FROM RAW JSON (ITERATION 1) ===")
configs = ["new_vs_basic", "basic_vs_new", "safety_vs_basic", "basic_vs_safety", "new_solo", "safety_solo"]

# For each config, identify which bot is our bot:
# new_vs_basic: bot 1 is new_bot, bot 2 is basic_bot
# basic_vs_new: bot 1 is basic_bot, bot 2 is new_bot
# safety_vs_basic: bot 1 is safety_bot, bot 2 is basic_bot
# basic_vs_safety: bot 1 is basic_bot, bot 2 is safety_bot
# new_solo: bot 1 is new_bot
# safety_solo: bot 1 is safety_bot

our_bot_roles = {
    "new_vs_basic": "1",
    "basic_vs_new": "2",
    "safety_vs_basic": "1",
    "basic_vs_safety": "2",
    "new_solo": "1",
    "safety_solo": "1",
}

for cfg in configs:
    matches = iter1[cfg]
    n = len(matches)
    our_id = our_bot_roles[cfg]
    opp_id = "2" if our_id == "1" else "1"
    is_head_to_head = len(matches[0]["bots"]) > 1

    scores = [m["bots"][our_id]["score"] for m in matches]
    opp_scores = [m["bots"][opp_id]["score"] for m in matches] if is_head_to_head else [0.0]*n
    colls = [m["bots"][our_id]["collections"] for m in matches]
    deps = [m["bots"][our_id]["deposits"] for m in matches]
    caps = [m["bots"][our_id]["captures"] for m in matches]
    lost = [m["bots"][our_id]["loot_lost"] for m in matches]
    bads = [m["bots"][our_id]["invalid_actions"] for m in matches]
    misses = [m["bots"][our_id]["misses"] for m in matches]
    holds = [m["bots"][our_id]["actions"]["HOLD"] for m in matches]
    traverses = [m["bots"][our_id]["actions"]["TRAVERSE"] for m in matches]
    col_acts = [m["bots"][our_id]["actions"]["COLLECT"] for m in matches]
    dep_acts = [m["bots"][our_id]["actions"]["DEPOSIT"] for m in matches]
    avg_ms_list = [m["bots"][our_id]["avg_ms"] for m in matches]
    max_ms_val = max(m["bots"][our_id]["max_ms"] for m in matches)

    wins = sum(1 for s, os_ in zip(scores, opp_scores) if s > os_) if is_head_to_head else 0
    losses = sum(1 for s, os_ in zip(scores, opp_scores) if s < os_) if is_head_to_head else 0
    ties = sum(1 for s, os_ in zip(scores, opp_scores) if s == os_) if is_head_to_head else 0

    print(f"\n--- {cfg.upper()} ---")
    print(f"Seeds evaluated: {[m['seed'] for m in matches]}")
    print(f"Our Bot ID: {our_id}")
    if is_head_to_head:
        print(f"Record (W-L-T): {wins}W - {losses}L - {ties}T (Win rate: {wins/n*100:.1f}%)")
        print(f"Our Average Score: {sum(scores)/n:.2f}")
        print(f"Opponent Average Score: {sum(opp_scores)/n:.2f}")
        print(f"Score Delta: {sum(scores)/n - sum(opp_scores)/n:+.2f}")
    else:
        print(f"Solo Average Score: {sum(scores)/n:.2f}")
    print(f"Average Collections: {sum(colls)/n:.2f}")
    print(f"Average Deposits: {sum(deps)/n:.2f}")
    print(f"Average Captures: {sum(caps)/n:.2f} (Total captures: {sum(caps)})")
    print(f"Average Loot Lost: ${sum(lost)/n:.2f} (Total loot lost: ${sum(lost):.2f})")
    print(f"Average Invalid Actions (BadActs): {sum(bads)/n:.2f} (Total: {sum(bads)})")
    print(f"Average Missed Actions: {sum(misses)/n:.2f} (Total: {sum(misses)})")
    print(f"Average HOLD count: {sum(holds)/n:.2f}")
    print(f"Average TRAVERSE count: {sum(traverses)/n:.2f}")
    print(f"Average COLLECT count: {sum(col_acts)/n:.2f}")
    print(f"Average DEPOSIT count: {sum(dep_acts)/n:.2f}")
    print(f"Average Latency: {sum(avg_ms_list)/n:.2f} ms (Peak: {max_ms_val:.2f} ms)")
    print(f"Seed-by-seed HOLDs: {dict(zip([m['seed'] for m in matches], holds))}")
    print(f"Seed-by-seed Scores: {dict(zip([m['seed'] for m in matches], [round(s, 1) for s in scores]))}")
    if is_head_to_head:
        print(f"Seed-by-seed Opponent Scores: {dict(zip([m['seed'] for m in matches], [round(s, 1) for s in opp_scores]))}")
