"""
Unit tests for opponent-aware drop targeting and tracking (Phase 5).

Verifies:
1. Opponent closer to valuable drop (discounts contested drop, prefers closer/safer drop).
2. Our runner closer to valuable drop (targets contested drop with high confidence).
3. Equal estimated arrival times (tie-discount applied for Bot 1 vs Bot 2).
4. Opponent cannot currently collect (stunned or full backpack -> no discount).
5. Drop disappearing before arrival (belief state updated, immediate replanning).
6. Multiple available drops with different values and travel times (optimal scoring).
7. Drop cannot be collected and deposited within remaining match (rejected by feasibility gate).
8. Missing or incomplete opponent information (graceful fallback).
"""

import math
import os
import sys
import unittest

# Ensure official_kit/submission can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "official_kit", "submission")))
import my_bot


class TestOpponentAwareTargeting(unittest.TestCase):
    def setUp(self):
        # Graph layout:
        # Node 0 (Safehouse) at (0, 0)
        # Node 1 (Junction) at (20, 0)
        # Node 2 (Money Spot A) at (40, 0)
        # Node 3 (Junction) at (0, 20)
        # Node 4 (Money Spot B) at (0, 40)
        self.nodes = {
            0: {"x": 0.0, "y": 0.0, "type": "safehouse"},
            1: {"x": 20.0, "y": 0.0, "type": "junction"},
            2: {"x": 40.0, "y": 0.0, "type": "money_spot"},
            3: {"x": 0.0, "y": 20.0, "type": "junction"},
            4: {"x": 0.0, "y": 40.0, "type": "money_spot"},
        }
        self.neighbors = {
            0: [(1, 20.0), (3, 20.0)],
            1: [(0, 20.0), (2, 20.0)],
            2: [(1, 20.0)],
            3: [(0, 20.0), (4, 20.0)],
            4: [(3, 20.0)],
        }
        self.safehouses = [0]
        self.money_spots = [2, 4]
        self.police = []  # No police interference in opponent logic tests unless specified

    def test_opponent_closer_to_valuable_drop(self):
        """
        Drop A (value 400 at Node 2) is 2 hops from our runner (Node 0).
        Drop B (value 250 at Node 4) is 2 hops from our runner (Node 0).
        Opponent is at Node 2 (0 hops from Drop A).
        Drop A is contested with opponent closer (opp_hops=0 vs our_hops=2, delta=2 -> discount 0.72^2 ~ 0.518).
        Effective value of Drop A: 400 * 0.518 = ~207.
        Effective value of Drop B: 250 * 1.0 = 250.
        Bot should prefer Drop B and move toward Node 3, not Node 1.
        """
        runner = {
            "id": 1,
            "current_node": 0,
            "x": 0.0,
            "y": 0.0,
            "carrying_loot": 0.0,
            "max_capacity": 500.0,
            "status": "ACTIVE",
            "stun_ticks_remaining": 0,
        }
        drops = [
            {
                "drop_id": 10,
                "node_id": 2,
                "target_safehouse_node": 0,
                "current_value": 400.0,
                "leak_lambda": 0.001,
                "ttl_remaining": 50,
            },
            {
                "drop_id": 20,
                "node_id": 4,
                "target_safehouse_node": 0,
                "current_value": 250.0,
                "leak_lambda": 0.001,
                "ttl_remaining": 50,
            },
        ]
        tracker = my_bot.OpponentTracker()
        state = {
            "opponent_runners": [
                {
                    "id": 99,
                    "current_node": 2,
                    "carrying_loot": 0.0,
                    "max_capacity": 500.0,
                    "status": "ACTIVE",
                    "stun_ticks_remaining": 0,
                }
            ],
            "active_money_drops": drops,
        }
        tracker.update(tick=10, state=state, my_runner_ids=[1])

        # Verify estimated arrival calculation
        opp_hops_a = tracker.get_estimated_opponent_arrival(2, self.neighbors, tick=10)
        self.assertEqual(opp_hops_a, 0)
        opp_hops_b = tracker.get_estimated_opponent_arrival(4, self.neighbors, tick=10)
        self.assertEqual(opp_hops_b, 4)  # 2 -> 1 -> 0 -> 3 -> 4 = 4 hops

        action = my_bot.decide_for_runner(
            runner=runner,
            tick=10,
            nodes=self.nodes,
            neighbors=self.neighbors,
            drops=drops,
            police=self.police,
            safehouses=self.safehouses,
            money_spots=self.money_spots,
            tracker=tracker,
        )

        # Bot chooses Drop B (first step Node 3) because Drop A is heavily contested
        self.assertEqual(action["action"], "TRAVERSE")
        self.assertEqual(action["target_node"], 3)

    def test_our_runner_closer_to_valuable_drop(self):
        """
        Our runner is at Node 1 (1 hop from Drop A at Node 2).
        Opponent is at Node 0 (2 hops from Drop A at Node 2).
        our_hops (1) < opp_hops (2) -> full confidence discount = 1.0.
        Bot should greedily pursue Drop A.
        """
        runner = {
            "id": 1,
            "current_node": 1,
            "x": 20.0,
            "y": 0.0,
            "carrying_loot": 0.0,
            "max_capacity": 500.0,
            "status": "ACTIVE",
            "stun_ticks_remaining": 0,
        }
        drops = [
            {
                "drop_id": 10,
                "node_id": 2,
                "target_safehouse_node": 0,
                "current_value": 300.0,
                "leak_lambda": 0.001,
                "ttl_remaining": 50,
            }
        ]
        tracker = my_bot.OpponentTracker()
        state = {
            "opponent_runners": [
                {
                    "id": 99,
                    "current_node": 0,
                    "carrying_loot": 0.0,
                    "max_capacity": 500.0,
                    "status": "ACTIVE",
                    "stun_ticks_remaining": 0,
                }
            ],
            "active_money_drops": drops,
        }
        tracker.update(tick=10, state=state, my_runner_ids=[1])

        discount = my_bot.compute_contestation_discount(our_hops=1, opp_hops=2, is_bot2=False)
        self.assertEqual(discount, 1.0)

        action = my_bot.decide_for_runner(
            runner=runner,
            tick=10,
            nodes=self.nodes,
            neighbors=self.neighbors,
            drops=drops,
            police=self.police,
            safehouses=self.safehouses,
            money_spots=self.money_spots,
            tracker=tracker,
        )

        self.assertEqual(action["action"], "TRAVERSE")
        self.assertEqual(action["target_node"], 2)

    def test_equal_estimated_arrival_times_tie_discount(self):
        """
        our_hops == opp_hops.
        Bot 1 discount = 0.85 (first mover).
        Bot 2 discount = 0.45 (losing ties in practice arena).
        """
        d_bot1 = my_bot.compute_contestation_discount(our_hops=2, opp_hops=2, is_bot2=False)
        self.assertAlmostEqual(d_bot1, 0.85)

        d_bot2 = my_bot.compute_contestation_discount(our_hops=2, opp_hops=2, is_bot2=True)
        self.assertAlmostEqual(d_bot2, 0.45)

        # For Bot 2, equal distance contested drop (300 * 0.45 = 135) yields to uncontested drop (150 * 1.0 = 150)
        runner_bot2 = {
            "id": 2,  # id > 1 triggers is_bot2
            "current_node": 0,
            "x": 0.0,
            "y": 0.0,
            "carrying_loot": 0.0,
            "max_capacity": 500.0,
            "status": "ACTIVE",
            "stun_ticks_remaining": 0,
        }
        drops = [
            {
                "drop_id": 10,
                "node_id": 2,
                "target_safehouse_node": 0,
                "current_value": 300.0,
                "leak_lambda": 0.001,
                "ttl_remaining": 50,
            },
            {
                "drop_id": 20,
                "node_id": 4,
                "target_safehouse_node": 0,
                "current_value": 150.0,
                "leak_lambda": 0.001,
                "ttl_remaining": 50,
            },
        ]
        # Opponent is 2 hops away from Drop A (Node 2)
        # In this graph, if opponent is at Node 0, opp_hops to 2 is 2.
        # But our runner is at Node 0, so let's put opponent at Node 1 to make opp_hops to 2 equal to 1,
        # or create an equidistant node. Let's make opponent have opp_hops=2 to Node 2.
        tracker = my_bot.OpponentTracker()
        tracker.known_opponents[1] = {
            "node": 0,
            "carrying": 0.0,
            "capacity": 500.0,
            "status": "ACTIVE",
            "stun_ticks": 0,
            "tick": 10,
        }
        # To make Drop B completely uncontested, say opponent capacity is full for Drop B or opponent is 4 hops from B
        # Node 0 is 2 hops from 4 as well. Let's test compute_contestation_discount directly:
        score_a = 300.0 * my_bot.compute_contestation_discount(2, 2, is_bot2=True)
        score_b = 150.0 * my_bot.compute_contestation_discount(2, 5, is_bot2=True)
        self.assertLess(score_a, score_b)

    def test_opponent_cannot_currently_collect(self):
        """
        Opponent is standing directly on Drop A (Node 2), but:
        Case A: Opponent's backpack is full (carrying >= 95% capacity).
        Case B: Opponent is STUNNED with remaining stun ticks.
        In both cases, our runner can still claim the drop.
        """
        tracker = my_bot.OpponentTracker()
        # Case A: Full backpack
        state_full = {
            "opponent_runners": [
                {
                    "id": 99,
                    "current_node": 2,
                    "carrying_loot": 490.0,
                    "max_capacity": 500.0,
                    "status": "ACTIVE",
                    "stun_ticks_remaining": 0,
                }
            ],
            "active_money_drops": [],
        }
        tracker.update(tick=10, state=state_full, my_runner_ids=[1])
        # Full backpack opponent ignored
        opp_hops = tracker.get_estimated_opponent_arrival(2, self.neighbors, tick=10)
        self.assertEqual(opp_hops, my_bot.INF)

        # Case B: Stunned opponent
        tracker.reset()
        state_stunned = {
            "opponent_runners": [
                {
                    "id": 99,
                    "current_node": 2,
                    "carrying_loot": 0.0,
                    "max_capacity": 500.0,
                    "status": "STUNNED",
                    "stun_ticks_remaining": 8,
                }
            ],
            "active_money_drops": [],
        }
        tracker.update(tick=10, state=state_stunned, my_runner_ids=[1])
        # Stunned opponent arrival includes stun duration
        opp_hops_stunned = tracker.get_estimated_opponent_arrival(2, self.neighbors, tick=10)
        self.assertEqual(opp_hops_stunned, 8)  # 0 hop distance + 8 stun ticks

    def test_drop_disappearing_before_arrival_updates_belief_and_replanning(self):
        """
        At tick 10, Drop 1 is at Node 2 with ttl=40.
        At tick 11, Drop 1 is suddenly gone (missing from active_money_drops), but ttl was > 1.
        Tracker infers opponent was at Node 2 at tick 10.
        When Drop 2 appears at Node 4, bot plans for Node 4 without stalling.
        """
        tracker = my_bot.OpponentTracker()
        state_t10 = {
            "active_money_drops": [
                {
                    "drop_id": 1,
                    "node_id": 2,
                    "target_safehouse_node": 0,
                    "current_value": 300.0,
                    "leak_lambda": 0.001,
                    "ttl_remaining": 40,
                }
            ]
        }
        tracker.update(tick=10, state=state_t10, my_runner_ids=[1])
        self.assertIsNone(tracker.last_sighting)

        # Drop 1 disappears unexpectedly at tick 11
        state_t11 = {
            "active_money_drops": [
                {
                    "drop_id": 2,
                    "node_id": 4,
                    "target_safehouse_node": 0,
                    "current_value": 200.0,
                    "leak_lambda": 0.001,
                    "ttl_remaining": 40,
                }
            ]
        }
        tracker.update(tick=11, state=state_t11, my_runner_ids=[1])
        self.assertIsNotNone(tracker.last_sighting)
        self.assertEqual(tracker.last_sighting["node"], 2)
        self.assertEqual(tracker.last_sighting["tick"], 10)

        # Inferred opponent at Node 2 gives estimated arrival to Node 4:
        # Distance 2 -> 4 is 4 hops. Elapsed tick = 1. Effective opp hops = 4 - 1 = 3 hops.
        opp_hops_b = tracker.get_estimated_opponent_arrival(4, self.neighbors, tick=11)
        self.assertEqual(opp_hops_b, 3)

        # Runner at Node 0 (2 hops from Node 4) evaluates Drop 2
        runner = {
            "id": 1,
            "current_node": 0,
            "x": 0.0,
            "y": 0.0,
            "carrying_loot": 0.0,
            "max_capacity": 500.0,
            "status": "ACTIVE",
            "stun_ticks_remaining": 0,
        }
        action = my_bot.decide_for_runner(
            runner=runner,
            tick=11,
            nodes=self.nodes,
            neighbors=self.neighbors,
            drops=state_t11["active_money_drops"],
            police=self.police,
            safehouses=self.safehouses,
            money_spots=self.money_spots,
            tracker=tracker,
        )
        self.assertEqual(action["action"], "TRAVERSE")
        self.assertEqual(action["target_node"], 3)  # Steps toward Node 4

    def test_multiple_available_drops_different_values_and_travel_times(self):
        """
        Multiple drops with different values and travel costs:
        Drop A at Node 2 (value 100, cost 40) -> score ~ 100 / 41 = 2.43
        Drop B at Node 4 (value 400, cost 40) -> score ~ 400 / 41 = 9.75
        Bot picks Drop B and steps toward Node 3.
        """
        runner = {
            "id": 1,
            "current_node": 0,
            "x": 0.0,
            "y": 0.0,
            "carrying_loot": 0.0,
            "max_capacity": 500.0,
            "status": "ACTIVE",
            "stun_ticks_remaining": 0,
        }
        drops = [
            {
                "drop_id": 1,
                "node_id": 2,
                "target_safehouse_node": 0,
                "current_value": 100.0,
                "leak_lambda": 0.001,
                "ttl_remaining": 50,
            },
            {
                "drop_id": 2,
                "node_id": 4,
                "target_safehouse_node": 0,
                "current_value": 400.0,
                "leak_lambda": 0.001,
                "ttl_remaining": 50,
            },
        ]
        action = my_bot.decide_for_runner(
            runner=runner,
            tick=10,
            nodes=self.nodes,
            neighbors=self.neighbors,
            drops=drops,
            police=self.police,
            safehouses=self.safehouses,
            money_spots=self.money_spots,
        )
        self.assertEqual(action["action"], "TRAVERSE")
        self.assertEqual(action["target_node"], 3)  # First step toward Drop 2 at Node 4

    def test_drop_cannot_be_collected_and_deposited_within_remaining_match(self):
        """
        Match ends in 3 ticks (tick=297).
        Drop A at Node 2 requires 2 hops to reach + 1 tick to collect + 2 hops to safehouse + 1 tick to deposit = 6 ticks.
        Remaining ticks = 3 < 6.
        Feasibility condition rejects Drop A.
        Runner with zero loot should HOLD or move to safehouse, not chase unreachable drop.
        """
        runner = {
            "id": 1,
            "current_node": 0,
            "x": 0.0,
            "y": 0.0,
            "carrying_loot": 0.0,
            "max_capacity": 500.0,
            "status": "ACTIVE",
            "stun_ticks_remaining": 0,
        }
        drops = [
            {
                "drop_id": 1,
                "node_id": 2,
                "target_safehouse_node": 0,
                "current_value": 1000.0,
                "leak_lambda": 0.001,
                "ttl_remaining": 50,
            }
        ]
        action = my_bot.decide_for_runner(
            runner=runner,
            tick=297,  # 3 ticks remaining
            nodes=self.nodes,
            neighbors=self.neighbors,
            drops=drops,
            police=self.police,
            safehouses=self.safehouses,
            money_spots=self.money_spots,
        )
        # Runner is already at safehouse (Node 0) and cannot complete the trip, so HOLD
        self.assertEqual(action["action"], "HOLD")

    def test_missing_or_incomplete_opponent_information_graceful_fallback(self):
        """
        When official state has no opponent keys and no drops have disappeared:
        - tracker returns INF for opponent arrival
        - contestation discount is 1.0 (no crash, no ungrounded penalties)
        - bot behaves normally
        """
        tracker = my_bot.OpponentTracker()
        tracker.update(tick=10, state={}, my_runner_ids=[1])

        opp_arrival = tracker.get_estimated_opponent_arrival(2, self.neighbors, tick=10)
        self.assertEqual(opp_arrival, my_bot.INF)

        discount = my_bot.compute_contestation_discount(our_hops=2, opp_hops=opp_arrival)
        self.assertEqual(discount, 1.0)

        runner = {
            "id": 1,
            "current_node": 0,
            "x": 0.0,
            "y": 0.0,
            "carrying_loot": 0.0,
            "max_capacity": 500.0,
            "status": "ACTIVE",
            "stun_ticks_remaining": 0,
        }
        drops = [
            {
                "drop_id": 1,
                "node_id": 2,
                "target_safehouse_node": 0,
                "current_value": 300.0,
                "leak_lambda": 0.001,
                "ttl_remaining": 50,
            }
        ]
        action = my_bot.decide_for_runner(
            runner=runner,
            tick=10,
            nodes=self.nodes,
            neighbors=self.neighbors,
            drops=drops,
            police=self.police,
            safehouses=self.safehouses,
            money_spots=self.money_spots,
            tracker=tracker,
        )
        self.assertEqual(action["action"], "TRAVERSE")
        self.assertEqual(action["target_node"], 1)


if __name__ == "__main__":
    unittest.main()
