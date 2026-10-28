import json

with open("practice_logs/opponent_aware_benchmark.json", "r", encoding="utf-8") as f:
    data = json.load(f)["iteration_1"]

def analyze_config(name, my_bot_id="1"):
    matches = data[name]
    n = len(matches)
    tot_score = sum(m["bots"][my_bot_id]["score"] for m in matches)
    tot_col = sum(m["bots"][my_bot_id]["collections"] for m in matches)
    tot_dep = sum(m["bots"][my_bot_id]["deposits"] for m in matches)
    tot_cap = sum(m["bots"][my_bot_id]["captures"] for m in matches)
    tot_lost = sum(m["bots"][my_bot_id]["loot_lost"] for m in matches)
    tot_bad = sum(m["bots"][my_bot_id]["invalid_actions"] for m in matches)
    tot_miss = sum(m["bots"][my_bot_id]["misses"] for m in matches)
    tot_hold = sum(m["bots"][my_bot_id]["actions"]["HOLD"] for m in matches)
    avg_ms = sum(m["bots"][my_bot_id]["avg_ms"] for m in matches) / n
    max_ms = max(m["bots"][my_bot_id]["max_ms"] for m in matches)

    wins, ties, losses = 0, 0, 0
    opp_id = "2" if my_bot_id == "1" else "1"
    opp_score = 0.0
    if len(matches[0]["bots"]) > 1:
        opp_score = sum(m["bots"][opp_id]["score"] for m in matches)
        for m in matches:
            s1 = m["bots"][my_bot_id]["score"]
            s2 = m["bots"][opp_id]["score"]
            if s1 > s2:
                wins += 1
            elif s1 == s2:
                ties += 1
            else:
                losses += 1

    return {
        "avg_score": tot_score / n,
        "opp_avg_score": opp_score / n if len(matches[0]["bots"]) > 1 else 0.0,
        "w_l_t": f"{wins}W - {losses}L - {ties}T",
        "avg_col": tot_col / n,
        "avg_dep": tot_dep / n,
        "avg_cap": tot_cap / n,
        "avg_lost": tot_lost / n,
        "avg_bad": tot_bad / n,
        "avg_miss": tot_miss / n,
        "avg_hold": tot_hold / n,
        "avg_ms": avg_ms,
        "max_ms": max_ms,
        "seed_holds": {m["seed"]: m["bots"][my_bot_id]["actions"]["HOLD"] for m in matches},
        "seed_scores": {m["seed"]: round(m["bots"][my_bot_id]["score"], 1) for m in matches},
    }

print("=== NEW BOT VS BASIC ===")
print(json.dumps(analyze_config("new_vs_basic", "1"), indent=2))

print("=== BASIC VS NEW (NEW IS BOT 2) ===")
print(json.dumps(analyze_config("basic_vs_new", "2"), indent=2))

print("=== SAFETY BOT VS BASIC ===")
print(json.dumps(analyze_config("safety_vs_basic", "1"), indent=2))

print("=== BASIC VS SAFETY (SAFETY IS BOT 2) ===")
print(json.dumps(analyze_config("basic_vs_safety", "2"), indent=2))

print("=== NEW BOT SOLO ===")
print(json.dumps(analyze_config("new_solo", "1"), indent=2))

print("=== SAFETY BOT SOLO ===")
print(json.dumps(analyze_config("safety_solo", "1"), indent=2))
