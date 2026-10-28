#!/usr/bin/env python3
"""
Inspect exact invalid action messages from practice logs for Bot 2.
Determines:
- Exact breakdown of action types (COLLECT, TRAVERSE, DEPOSIT, etc.)
- Whether they are simultaneous contested collections vs bot errors
- Whether invalid actions penalize score or simply result in a wasted tick
"""

import os
import glob
import re

log_dir = os.path.join(os.path.dirname(__file__), "practice_logs")

# Check matches where Candidate was Bot 2 (Position 2, seeds 100-199)
# In run_match, stderr logs were written for each match.
# Also, let's run a short 5-seed sample of Position 2 with verbose=True to capture the engine's exact reasons.
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "practice_arena"))
from practice_arena import PracticeArena

class VerboseArena(PracticeArena):
    def __init__(self, commands, seed=1, ticks=300):
        super().__init__(commands, seed=seed, ticks=ticks, verbose=True, log_dir="practice_logs")
        self.invalid_reasons = []

    def _say(self, text):
        if "illegal" in text or "COLLECT with nothing" in text or "DEPOSIT not possible" in text or "unknown action" in text:
            self.invalid_reasons.append(text)

py = sys.executable
base_dir = os.path.dirname(os.path.abspath(__file__))
bot_baseline = [py, os.path.join(base_dir, "submission", "my_bot.py")]
bot_candidate = [py, os.path.join(base_dir, "submission", "my_bot_experimental.py")]

print("Running 10 test matches of Position 2 (Baseline=Bot 1, Candidate=Bot 2) with verbose error interception...")
reasons = {}
for seed in range(100, 110):
    arena = VerboseArena([bot_baseline, bot_candidate], seed=seed, ticks=300)
    arena.run()
    for r in arena.invalid_reasons:
        reasons[r] = reasons.get(r, 0) + 1

print("\nExact Invalid Action Messages Captured for Bot 2:")
for msg, count in sorted(reasons.items(), key=lambda x: -x[1]):
    print(f"  [{count}x] {msg}")

