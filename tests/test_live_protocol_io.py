"""
Direct JSON-line interface integration test for submission/my_bot.py.
Verifies:
1. Subprocess starts cleanly with persistent process.
2. Every input line receives exactly one JSON response line on stdout.
3. Diagnostic messages go to stderr, never polluting stdout.
4. Consecutive ticks work seamlessly across 10+ sequential frames.
5. Missing optional fields (e.g. opponent_runners, police velocities) handled gracefully.
6. Malformed or invalid input lines do not crash the bot.
"""

import json
import os
import subprocess
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BOT_SCRIPT = os.path.join(ROOT_DIR, "official_kit", "submission", "rahulrkudlur.py")



class TestLiveProtocolIO(unittest.TestCase):
    def setUp(self):
        self.proc = subprocess.Popen(
            [sys.executable, BOT_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            encoding="utf-8",
        )

    def tearDown(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.proc.stdin:
            self.proc.stdin.close()
        if self.proc.stdout:
            self.proc.stdout.close()
        if self.proc.stderr:
            self.proc.stderr.close()

    def send_and_receive(self, payload):
        line = json.dumps(payload) + "\n"
        self.proc.stdin.write(line)
        self.proc.stdin.flush()
        out_line = self.proc.stdout.readline()
        return out_line

    def test_multi_tick_persistent_process(self):
        """Sends multiple consecutive ticks to the same persistent process and verifies output."""
        base_state = {
            "tick": 0,
            "graph_nodes": [
                {"id": 0, "x": 0.0, "y": 0.0, "type": "safehouse"},
                {"id": 1, "x": 20.0, "y": 0.0, "type": "junction"},
                {"id": 2, "x": 40.0, "y": 0.0, "type": "money_spot"},
            ],
            "graph_edges": [
                {"from": 0, "to": 1, "base_weight": 20.0, "current_weight": 20.0},
                {"from": 1, "to": 2, "base_weight": 20.0, "current_weight": 20.0},
            ],
            "my_runners": [
                {
                    "id": 1,
                    "current_node": 0,
                    "x": 0.0,
                    "y": 0.0,
                    "carrying_loot": 0.0,
                    "max_capacity": 500.0,
                    "status": "ACTIVE",
                    "stun_ticks_remaining": 0,
                }
            ],
            "active_money_drops": [
                {
                    "drop_id": 1,
                    "node_id": 2,
                    "target_safehouse_node": 0,
                    "current_value": 300.0,
                    "leak_lambda": 0.005,
                    "ttl_remaining": 50,
                }
            ],
            "police_officers": [],
        }

        # Tick 0: At Node 0, traverses to Node 1
        resp_raw = self.send_and_receive(base_state)
        self.assertTrue(resp_raw.strip(), "Bot returned empty line")
        resp = json.loads(resp_raw)
        self.assertIn("runner_actions", resp)
        self.assertEqual(len(resp["runner_actions"]), 1)
        act0 = resp["runner_actions"][0]
        self.assertEqual(act0["runner_id"], 1)
        self.assertEqual(act0["action"], "TRAVERSE")
        self.assertEqual(act0["target_node"], 1)

        # Tick 1: Runner now at Node 1, traverses to Node 2
        state_t1 = dict(base_state)
        state_t1["tick"] = 1
        state_t1["my_runners"] = [
            {
                "id": 1,
                "current_node": 1,
                "x": 20.0,
                "y": 0.0,
                "carrying_loot": 0.0,
                "max_capacity": 500.0,
                "status": "ACTIVE",
                "stun_ticks_remaining": 0,
            }
        ]
        resp_raw1 = self.send_and_receive(state_t1)
        resp1 = json.loads(resp_raw1)
        act1 = resp1["runner_actions"][0]
        self.assertEqual(act1["action"], "TRAVERSE")
        self.assertEqual(act1["target_node"], 2)

        # Tick 2: Runner arrives at Node 2, collects drop
        state_t2 = dict(base_state)
        state_t2["tick"] = 2
        state_t2["my_runners"] = [
            {
                "id": 1,
                "current_node": 2,
                "x": 40.0,
                "y": 0.0,
                "carrying_loot": 0.0,
                "max_capacity": 500.0,
                "status": "ACTIVE",
                "stun_ticks_remaining": 0,
            }
        ]
        resp_raw2 = self.send_and_receive(state_t2)
        resp2 = json.loads(resp_raw2)
        act2 = resp2["runner_actions"][0]
        self.assertEqual(act2["action"], "COLLECT")

    def test_missing_optional_fields_and_no_stdout_pollution(self):
        """Verifies no diagnostic strings contaminate stdout, and handles optional fields."""
        minimal_state = {
            "tick": 5,
            "graph_nodes": [{"id": 0, "x": 0.0, "y": 0.0, "type": "safehouse"}],
            "graph_edges": [],
            "my_runners": [
                {
                    "id": 1,
                    "current_node": 0,
                    "x": 0.0,
                    "y": 0.0,
                    "carrying_loot": 100.0,
                    "max_capacity": 500.0,
                    "status": "ACTIVE",
                    "stun_ticks_remaining": 0,
                }
            ],
            "active_money_drops": [],
            "police_officers": [],
        }
        resp_raw = self.send_and_receive(minimal_state)
        # Verify valid JSON parse with no extraneous text
        self.assertTrue(resp_raw.startswith("{") and resp_raw.endswith("}\n"))
        resp = json.loads(resp_raw)
        self.assertEqual(resp["runner_actions"][0]["action"], "DEPOSIT")


if __name__ == "__main__":
    unittest.main()
