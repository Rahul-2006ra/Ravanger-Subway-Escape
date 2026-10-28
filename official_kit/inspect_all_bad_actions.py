import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "practice_arena"))
from practice_arena import PracticeArena

class BadActionInspectorArena(PracticeArena):
    def __init__(self, commands, seed=1, ticks=300):
        super().__init__(commands, seed=seed, ticks=ticks, verbose=False)
        self.bad_action_events = []

    def _say(self, text):
        if "illegal" in text or "COLLECT with nothing" in text or "illegal TRAVERSE" in text:
            self.bad_action_events.append({"tick": self.tick, "msg": text})

py = sys.executable
base_dir = os.path.dirname(os.path.abspath(__file__))
basic_bot = [py, os.path.join(base_dir, "sample_bot", "python", "basic_bot.py")]
new_bot = [py, os.path.join(base_dir, "submission", "my_bot.py")]
safety_bot = [py, os.path.join(base_dir, "submission", "my_bot_safety.py")]

print("=== INSPECTING ALL 56 INVALID ACTIONS IN BASIC_VS_NEW (SEEDS 100-109) ===")
total_bads = 0
reasons_count = {}
for seed in range(100, 110):
    arena = BadActionInspectorArena([basic_bot, new_bot], seed=seed, ticks=300)
    stats = arena.run()
    b2_bad = stats[2].invalid_actions
    total_bads += b2_bad
    print(f"Seed {seed}: Bot 2 bad={b2_bad}, events={len(arena.bad_action_events)}")
    for ev in arena.bad_action_events:
        msg = ev["msg"]
        if "Bot 2" in msg:
            if "COLLECT with nothing to collect" in msg:
                reasons_count["COLLECT_NOTHING"] = reasons_count.get("COLLECT_NOTHING", 0) + 1
            elif "illegal TRAVERSE" in msg:
                reasons_count["ILLEGAL_TRAVERSE"] = reasons_count.get("ILLEGAL_TRAVERSE", 0) + 1
                print(f"  --> ALERT: ILLEGAL TRAVERSE on seed {seed} tick {ev['tick']}: {msg}")
            else:
                reasons_count["OTHER"] = reasons_count.get("OTHER", 0) + 1
                print(f"  --> OTHER on seed {seed} tick {ev['tick']}: {msg}")

print(f"\nTotal Bot 2 Bad Actions: {total_bads}")
print(f"Reason breakdown: {reasons_count}")
