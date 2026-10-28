import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "practice_arena"))
from practice_arena import PracticeArena

class LoggingArena(PracticeArena):
    def _say(self, text):
        if "illegal" in text or "COLLECT with nothing" in text or "Bot 2:" in text:
            print(f"[Tick {self.tick}] {text}")

py = sys.executable
base_dir = os.path.dirname(os.path.abspath(__file__))
basic_bot = [py, os.path.join(base_dir, "sample_bot", "python", "basic_bot.py")]
new_bot = [py, os.path.join(base_dir, "submission", "my_bot.py")]

arena = LoggingArena([basic_bot, new_bot], seed=100, ticks=300, verbose=False)
stats = arena.run()
print(f"Stats: Bot 1 bad={stats[1].invalid_actions}, Bot 2 bad={stats[2].invalid_actions}")
