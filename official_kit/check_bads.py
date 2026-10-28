import json

with open("practice_logs/opponent_aware_benchmark.json", "r", encoding="utf-8") as f:
    matches = json.load(f)["iteration_1"]["basic_vs_new"]

for m in matches:
    b1_bad = m["bots"]["1"]["invalid_actions"]
    b2_bad = m["bots"]["2"]["invalid_actions"]
    b1_score = m["bots"]["1"]["score"]
    b2_score = m["bots"]["2"]["score"]
    print(f"Seed {m['seed']}: Bot 1 (basic) Bad={b1_bad}, Score={b1_score:.0f} | Bot 2 (new) Bad={b2_bad}, Score={b2_score:.0f}")

with open("practice_logs/opponent_aware_benchmark.json", "r", encoding="utf-8") as f:
    matches_safety = json.load(f)["iteration_1"]["basic_vs_safety"]

print("\n--- new_vs_basic ---")
with open("practice_logs/opponent_aware_benchmark.json", "r", encoding="utf-8") as f:
    matches_new = json.load(f)["iteration_1"]["new_vs_basic"]
for m in matches_new:
    b1_bad = m["bots"]["1"]["invalid_actions"]
    b2_bad = m["bots"]["2"]["invalid_actions"]
    print(f"Seed {m['seed']}: Bot 1 (new) Bad={b1_bad} | Bot 2 (basic) Bad={b2_bad}")

