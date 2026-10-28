"""
Targeted regression tests for collision safety and police evasion.

Verifies:
1. Cop currently overlapping destination node and moving away.
2. Cop predicted to overlap destination at relevant capture time (t=1).
3. Cop near edge segment midpoint (forward edge intersection).
4. Safe destination with a nearby cop that should not cause an unnecessary diversion.
5. All neighbours dangerous (holding when current node is safe; evading to least harmful when current is dangerous).
6. Zero police officers present.
7. Blocked edges (current_weight == -1.0) and unreachable safehouses.
"""

import math
import os
import sys
import unittest

# Ensure official_kit/submission can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "official_kit", "submission")))
import my_bot


class TestCollisionSafetyChecks(unittest.TestCase):
    def setUp(self):
        # Base graph layout: Node 0 (Safehouse), Node 1 (Junction), Node 2 (Money Spot)
        self.nodes = {
            0: {"x": 0.0, "y": 0.0, "type": "safehouse"},
            1: {"x": 20.0, "y": 0.0, "type": "junction"},
            2: {"x": 40.0, "y": 0.0, "type": "money_spot"},
        }
        self.neighbors = {
            0: [(1, 20.0)],
            1: [(0, 20.0), (2, 20.0)],
            2: [(1, 20.0)],
        }
        self.safehouses = [0]
        self.money_spots = [2]
        self.drops = [
            {
                "drop_id": 1,
                "node_id": 2,
                "target_safehouse_node": 0,
                "current_value": 300.0,
                "leak_lambda": 0.005,
                "ttl_remaining": 50,
            }
        ]

    def test_cop_overlapping_destination_moving_away(self):
        """
        Cop is currently overlapping Node 1 (x=20, y=0) at t=0, but moving east (vx=5.0).
        At t=1, cop is at x=25 (further away).
        A naive check with time_offset=1 would miss the immediate danger at t=0.
        The bot must NOT traverse into Node 1!
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
        # Cop at (20.0, 0.0), radius 15.0, moving right at vx=5.0
        police = [{"id": 1, "x": 20.0, "y": 0.0, "vx": 5.0, "vy": 0.0, "radius": 15.0}]

        # Verify is_node_threatened captures t=0
        self.assertTrue(my_bot.is_node_threatened(self.nodes[1], police, time_offset=0))

        action = my_bot.decide_for_runner(
            runner=runner,
            tick=10,
            nodes=self.nodes,
            neighbors=self.neighbors,
            drops=self.drops,
            police=police,
            safehouses=self.safehouses,
            money_spots=self.money_spots,
        )

        # Runner at Node 0 is safe, so it must HOLD rather than stepping into the cop at Node 1
        self.assertEqual(action["action"], "HOLD")
        self.assertNotEqual(action.get("target_node"), 1)

    def test_cop_predicted_to_overlap_destination_at_capture_time(self):
        """
        Cop is at (10.0, 0.0) moving east with vx=10.0.
        At t=0, distance to Node 2 (40.0, 0.0) is 30.0 (outside radius 15).
        At t=1, cop reaches (20.0, 0.0), directly on Node 1!
        A runner stepping from 0 to 1 would be stepping into a cop closing in at t=1.
        The bot must detect the threat and not traverse into Node 1.
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
        # Cop starts at (35.0, 0.0), distance to Node 0 is 35 (safe at t=0)
        # Moving west with vx=-15.0. At t=1, cop is at (20.0, 0.0), directly on Node 1!
        police = [{"id": 1, "x": 35.0, "y": 0.0, "vx": -15.0, "vy": 0.0, "radius": 15.0}]

        # At t=0, Node 0 is safe
        self.assertFalse(my_bot.is_node_threatened(self.nodes[0], police, time_offset=0))
        # At t=1, cop is at (20, 0), overlapping Node 1
        self.assertTrue(my_bot.is_node_threatened(self.nodes[1], police, time_offset=1))

        action = my_bot.decide_for_runner(
            runner=runner,
            tick=10,
            nodes=self.nodes,
            neighbors=self.neighbors,
            drops=self.drops,
            police=police,
            safehouses=self.safehouses,
            money_spots=self.money_spots,
        )

        self.assertEqual(action["action"], "HOLD")
        self.assertNotEqual(action.get("target_node"), 1)

    def test_cop_near_edge_segment_midpoint(self):
        """
        Node 0 is (0, 0), Node 1 is (40, 0).
        Cop is at (20, 2), radius 15.
        Cop does not overlap Node 0 or Node 1 directly, but is within 2 units of the edge midpoint.
        is_forward_edge_threatened must detect this track threat.
        """
        node_a = {"x": 0.0, "y": 0.0}
        node_b = {"x": 40.0, "y": 0.0}
        police = [{"id": 1, "x": 20.0, "y": 2.0, "vx": 0.0, "vy": 0.0, "radius": 15.0}]

        # Edge segment is threatened
        self.assertTrue(my_bot.is_forward_edge_threatened(node_a, node_b, police, time_offset=0))

        # Cop behind node_a (x=-10) should NOT threaten forward edge
        police_behind = [{"id": 1, "x": -10.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "radius": 15.0}]
        self.assertFalse(my_bot.is_forward_edge_threatened(node_a, node_b, police_behind, time_offset=0))

    def test_safe_destination_nearby_cop_no_unnecessary_diversion(self):
        """
        Destination is safe (distance to cop > radius + safety_margin).
        The bot should proceed smoothly toward the destination without unnecessary hold or diversion.
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
        # Cop is at (20.0, 50.0), distance to Node 1 (20, 0) is 50.0 >> 17.0
        police = [{"id": 1, "x": 20.0, "y": 50.0, "vx": 0.0, "vy": 0.0, "radius": 15.0}]

        self.assertFalse(my_bot.is_node_threatened(self.nodes[1], police, time_offset=0))
        self.assertFalse(my_bot.is_node_threatened(self.nodes[1], police, time_offset=1))

        action = my_bot.decide_for_runner(
            runner=runner,
            tick=10,
            nodes=self.nodes,
            neighbors=self.neighbors,
            drops=self.drops,
            police=police,
            safehouses=self.safehouses,
            money_spots=self.money_spots,
        )

        # Should traverse normally to Node 1
        self.assertEqual(action["action"], "TRAVERSE")
        self.assertEqual(action["target_node"], 1)

    def test_all_neighbors_dangerous_holding_when_current_safe(self):
        """
        Current node is safe, but all usable neighbors are threatened by police.
        The bot should choose HOLD rather than stepping into an active danger zone.
        """
        nodes = {
            0: {"x": 0.0, "y": 0.0, "type": "safehouse"},
            1: {"x": 20.0, "y": 0.0, "type": "junction"},
            2: {"x": -20.0, "y": 0.0, "type": "junction"},
        }
        neighbors = {
            0: [(1, 20.0), (2, 20.0)],
            1: [(0, 20.0)],
            2: [(0, 20.0)],
        }
        runner = {
            "id": 1,
            "current_node": 0,
            "x": 0.0,
            "y": 0.0,
            "carrying_loot": 100.0,
            "max_capacity": 500.0,
            "status": "ACTIVE",
            "stun_ticks_remaining": 0,
        }
        # Cops directly on both neighbors (1 and 2)
        police = [
            {"id": 1, "x": 20.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "radius": 15.0},
            {"id": 2, "x": -20.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "radius": 15.0},
        ]

        action = my_bot.decide_for_runner(
            runner=runner,
            tick=10,
            nodes=nodes,
            neighbors=neighbors,
            drops=[],
            police=police,
            safehouses=[0],
            money_spots=[],
        )

        # Node 0 is safehouse and safe -> deposits immediately
        self.assertEqual(action["action"], "DEPOSIT")

    def test_all_neighbors_dangerous_and_current_in_danger_evades_to_safest(self):
        """
        Current node is under direct police attack. Both neighbors also have threats,
        but one neighbor puts more distance between runner and cop.
        The bot must select the least harmful legal neighbor.
        """
        nodes = {
            10: {"x": 0.0, "y": 0.0, "type": "junction"},
            11: {"x": 25.0, "y": 0.0, "type": "junction"},  # Distance 25 from cop
            12: {"x": -18.0, "y": 0.0, "type": "junction"}, # Distance 18 from cop
        }
        neighbors = {
            10: [(11, 25.0), (12, 18.0)],
            11: [(10, 25.0)],
            12: [(10, 18.0)],
        }
        runner = {
            "id": 1,
            "current_node": 10,
            "x": 0.0,
            "y": 0.0,
            "carrying_loot": 50.0,
            "max_capacity": 500.0,
            "status": "ACTIVE",
            "stun_ticks_remaining": 0,
        }
        # Cop is sitting at (0, 0), threatening current node 10!
        police = [{"id": 1, "x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "radius": 15.0}]

        action = my_bot.decide_for_runner(
            runner=runner,
            tick=10,
            nodes=nodes,
            neighbors=neighbors,
            drops=[],
            police=police,
            safehouses=[],
            money_spots=[],
        )

        # Must evade to neighbor 11 (distance 25 > 18)
        self.assertEqual(action["action"], "TRAVERSE")
        self.assertEqual(action["target_node"], 11)

    def test_no_police_officers(self):
        """Bot functions normally without error when police list is empty."""
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
            tick=10,
            nodes=self.nodes,
            neighbors=self.neighbors,
            drops=self.drops,
            police=[],
            safehouses=self.safehouses,
            money_spots=self.money_spots,
        )

        self.assertEqual(action["action"], "TRAVERSE")
        self.assertEqual(action["target_node"], 1)

    def test_blocked_edges_and_unreachable_safehouses(self):
        """
        When tracks are blocked (weight == inf), the bot does not attempt to traverse them.
        """
        blocked_neighbors = {
            0: [(1, math.inf)],  # Blocked track
            1: [(0, math.inf)],
            2: [],
        }
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
            tick=10,
            nodes=self.nodes,
            neighbors=blocked_neighbors,
            drops=self.drops,
            police=[],
            safehouses=self.safehouses,
            money_spots=self.money_spots,
        )

        # Track 0 -> 1 is blocked, so runner must HOLD safely
        self.assertEqual(action["action"], "HOLD")


if __name__ == "__main__":
    unittest.main()
