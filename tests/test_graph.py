"""Unit tests for the weighted graph pathfinding module."""

import copy
import math
import unittest
from typing import Dict, List, Mapping

from src.strategy.graph import (
    NodeId,
    ShortestPathResult,
    WeightedGraph,
    dijkstra_all,
    dijkstra_shortest_path,
)


class TestDijkstraPathfinding(unittest.TestCase):
    """Test suite for dijkstra_shortest_path and WeightedGraph."""

    def test_direct_shortest_path(self) -> None:
        """Verify direct edge is chosen when it is the strictly shortest path."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "A": {"B": 3.0, "C": 10.0},
            "B": {"C": 4.0},
            "C": {},
        }
        res = dijkstra_shortest_path(graph, "A", "B")
        self.assertEqual(res.cost, 3.0)
        self.assertEqual(res.path, ["A", "B"])

    def test_cheaper_multi_edge_path(self) -> None:
        """Verify indirect multi-hop route is chosen when total cost is lower than direct edge."""
        # Direct A -> C is 10.0, but A -> B -> C is 2.0 + 3.0 = 5.0
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "A": {"B": 2.0, "C": 10.0},
            "B": {"C": 3.0},
            "C": {},
        }
        res = dijkstra_shortest_path(graph, "A", "C")
        self.assertEqual(res.cost, 5.0)
        self.assertEqual(res.path, ["A", "B", "C"])

    def test_unreachable_target(self) -> None:
        """Verify unreachable destination returns path=None and cost=inf."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "A": {"B": 1.0},
            "B": {},
            "C": {"D": 2.0},
            "D": {},
        }
        res = dijkstra_shortest_path(graph, "A", "C")
        self.assertIsNone(res.path)
        self.assertTrue(math.isinf(res.cost))

    def test_blocked_edge_with_infinite_weight(self) -> None:
        """Verify edges with float('inf') weight are treated as blocked/impassable."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "A": {"B": float("inf"), "C": 5.0},
            "B": {"D": 1.0},
            "C": {"D": 2.0},
            "D": {},
        }
        res = dijkstra_shortest_path(graph, "A", "D")
        self.assertEqual(res.cost, 7.0)
        self.assertEqual(res.path, ["A", "C", "D"])

        # Fully blocked route returns unreachable
        blocked_only: Dict[NodeId, Dict[NodeId, float]] = {
            "A": {"B": float("inf")},
            "B": {},
        }
        res_blocked = dijkstra_shortest_path(blocked_only, "A", "B")
        self.assertIsNone(res_blocked.path)
        self.assertTrue(math.isinf(res_blocked.cost))

    def test_disconnected_graph(self) -> None:
        """Verify safe handling of isolated nodes with zero outgoing or incoming edges."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "A": {"B": 1.0},
            "B": {},
            "ISOLATED": {},
        }
        res = dijkstra_shortest_path(graph, "A", "ISOLATED")
        self.assertIsNone(res.path)
        self.assertTrue(math.isinf(res.cost))

    def test_source_equal_to_target(self) -> None:
        """Verify source == target returns single-node path with 0.0 cost."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "A": {"B": 2.0},
            "B": {"A": 2.0},
        }
        res = dijkstra_shortest_path(graph, "A", "A")
        self.assertEqual(res.cost, 0.0)
        self.assertEqual(res.path, ["A"])

    def test_zero_weight_edges(self) -> None:
        """Verify graphs with zero-weight edges calculate exact paths correctly."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "A": {"B": 0.0},
            "B": {"C": 0.0},
            "C": {"D": 5.0},
            "D": {},
        }
        res = dijkstra_shortest_path(graph, "A", "D")
        self.assertEqual(res.cost, 5.0)
        self.assertEqual(res.path, ["A", "B", "C", "D"])

    def test_negative_edge_weight_rejection(self) -> None:
        """Verify negative edge weights raise ValueError with an informative message."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "A": {"B": -1.0},
            "B": {},
        }
        with self.assertRaises(ValueError) as ctx:
            dijkstra_shortest_path(graph, "A", "B")
        self.assertIn("Negative edge weight", str(ctx.exception))

        # Also verify WeightedGraph.add_edge rejects negative weights
        wg = WeightedGraph()
        with self.assertRaises(ValueError):
            wg.add_edge("A", "B", -0.5)

    def test_empty_graph_or_missing_source(self) -> None:
        """Verify queries on empty graphs or missing nodes return unreachable safely."""
        empty_graph: Dict[NodeId, Dict[NodeId, float]] = {}
        res_empty = dijkstra_shortest_path(empty_graph, "A", "B")
        self.assertIsNone(res_empty.path)
        self.assertTrue(math.isinf(res_empty.cost))

        # Source not in graph
        graph: Dict[NodeId, Dict[NodeId, float]] = {"B": {"C": 1.0}, "C": {}}
        res_missing_src = dijkstra_shortest_path(graph, "A", "C")
        self.assertIsNone(res_missing_src.path)
        self.assertTrue(math.isinf(res_missing_src.cost))

        # Target not in graph
        res_missing_tgt = dijkstra_shortest_path(graph, "B", "NONEXISTENT")
        self.assertIsNone(res_missing_tgt.path)
        self.assertTrue(math.isinf(res_missing_tgt.cost))

    def test_multiple_equal_cost_paths(self) -> None:
        """Verify that when multiple paths share identical minimal cost, any valid path is accepted."""
        # Path 1: A -> B -> D (cost 1 + 2 = 3)
        # Path 2: A -> C -> D (cost 2 + 1 = 3)
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "A": {"B": 1.0, "C": 2.0},
            "B": {"D": 2.0},
            "C": {"D": 1.0},
            "D": {},
        }
        res = dijkstra_shortest_path(graph, "A", "D")
        self.assertEqual(res.cost, 3.0)
        self.assertIsNotNone(res.path)
        assert res.path is not None  # for type checking

        # Validate path structure without forcing tie-break preference
        self.assertEqual(res.path[0], "A")
        self.assertEqual(res.path[-1], "D")
        self.assertIn(res.path, [["A", "B", "D"], ["A", "C", "D"]])

    def test_does_not_modify_caller_graph(self) -> None:
        """Verify the caller's input dictionary remains completely unchanged."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "A": {"B": 2.0, "C": 5.0},
            "B": {"C": 1.0},
            "C": {},
        }
        backup = copy.deepcopy(graph)
        dijkstra_shortest_path(graph, "A", "C")
        self.assertEqual(graph, backup)

    def test_mixed_node_id_types(self) -> None:
        """Verify graph paths work smoothly when node IDs are a mix of strings and integers."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            1: {"station_two": 4.0, 3: 10.0},
            "station_two": {3: 2.0},
            3: {},
        }
        res = dijkstra_shortest_path(graph, 1, 3)
        self.assertEqual(res.cost, 6.0)
        self.assertEqual(res.path, [1, "station_two", 3])

    def test_weighted_graph_class_integration(self) -> None:
        """Verify WeightedGraph class instance works identically with dijkstra_shortest_path."""
        wg = WeightedGraph()
        wg.add_edge("X", "Y", 2.5, bidirectional=True)
        wg.add_edge("Y", "Z", 1.5, bidirectional=False)

        # Forward
        res_fwd = dijkstra_shortest_path(wg, "X", "Z")
        self.assertEqual(res_fwd.cost, 4.0)
        self.assertEqual(res_fwd.path, ["X", "Y", "Z"])

        # Backward: Z -> Y does not exist
        res_bwd = dijkstra_shortest_path(wg, "Z", "X")
        self.assertIsNone(res_bwd.path)
        self.assertTrue(math.isinf(res_bwd.cost))


class TestDijkstraAll(unittest.TestCase):
    """Test suite for dijkstra_all single-source multi-destination pathfinding."""

    def test_multiple_reachable_destinations(self) -> None:
        """Verify all reachable destinations are discovered with correct paths and costs."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "A": {"B": 1.0, "C": 4.0},
            "B": {"C": 2.0, "D": 5.0},
            "C": {"D": 1.0},
            "D": {},
        }
        res = dijkstra_all(graph, "A")

        self.assertEqual(set(res.keys()), {"A", "B", "C", "D"})
        self.assertEqual(res["A"].cost, 0.0)
        self.assertEqual(res["A"].path, ["A"])
        self.assertEqual(res["B"].cost, 1.0)
        self.assertEqual(res["B"].path, ["A", "B"])
        self.assertEqual(res["C"].cost, 3.0)
        self.assertEqual(res["C"].path, ["A", "B", "C"])
        self.assertEqual(res["D"].cost, 4.0)
        self.assertEqual(res["D"].path, ["A", "B", "C", "D"])

    def test_correct_shortest_costs_and_reconstructed_paths(self) -> None:
        """Verify path costs match the exact sum of edge weights along each reconstructed path."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "Root": {"N1": 10.0, "N2": 2.0},
            "N1": {"N3": 1.0},
            "N2": {"N1": 3.0, "N3": 8.0},
            "N3": {},
        }
        res = dijkstra_all(graph, "Root")

        # Root -> N2 -> N1 is cost 5, Root -> N2 -> N1 -> N3 is cost 6
        self.assertEqual(res["N1"].cost, 5.0)
        self.assertEqual(res["N1"].path, ["Root", "N2", "N1"])
        self.assertEqual(res["N3"].cost, 6.0)
        self.assertEqual(res["N3"].path, ["Root", "N2", "N1", "N3"])

        # Check path reconstruction validity for every node
        for node, path_res in res.items():
            self.assertEqual(path_res.path[0], "Root")
            self.assertEqual(path_res.path[-1], node)
            computed_cost = 0.0
            for u, v in zip(path_res.path[:-1], path_res.path[1:]):
                computed_cost += graph[u][v]
            self.assertAlmostEqual(computed_cost, path_res.cost)

    def test_unreachable_and_isolated_nodes(self) -> None:
        """Verify isolated and unreachable nodes are omitted from the reachable mapping."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "A": {"B": 2.0},
            "B": {},
            "ISOLATED": {},
            "UNREACHABLE_1": {"UNREACHABLE_2": 1.0},
            "UNREACHABLE_2": {},
        }
        res = dijkstra_all(graph, "A")

        self.assertIn("A", res)
        self.assertIn("B", res)
        self.assertNotIn("ISOLATED", res)
        self.assertNotIn("UNREACHABLE_1", res)
        self.assertNotIn("UNREACHABLE_2", res)
        self.assertIsNone(res.get("ISOLATED"))

    def test_infinite_weight_blocked_edges(self) -> None:
        """Verify nodes behind infinite-weight blocked edges are omitted unless reachable otherwise."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "A": {"BLOCKED_TARGET": float("inf"), "OPEN_INTERMEDIATE": 3.0},
            "OPEN_INTERMEDIATE": {"OPEN_TARGET": 2.0},
            "BLOCKED_TARGET": {},
            "OPEN_TARGET": {},
        }
        res = dijkstra_all(graph, "A")

        self.assertIn("OPEN_TARGET", res)
        self.assertEqual(res["OPEN_TARGET"].cost, 5.0)
        self.assertNotIn("BLOCKED_TARGET", res)

    def test_zero_weight_edges(self) -> None:
        """Verify graphs with zero-weight transitions calculate exact path costs."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "Start": {"T1": 0.0},
            "T1": {"T2": 0.0, "End": 5.0},
            "T2": {"End": 2.0},
            "End": {},
        }
        res = dijkstra_all(graph, "Start")

        self.assertEqual(res["Start"].cost, 0.0)
        self.assertEqual(res["T1"].cost, 0.0)
        self.assertEqual(res["T2"].cost, 0.0)
        self.assertEqual(res["End"].cost, 2.0)
        self.assertEqual(res["End"].path, ["Start", "T1", "T2", "End"])

    def test_mixed_node_id_types(self) -> None:
        """Verify single traversal works correctly when node IDs mix strings and integers."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            0: {1: 1.5, "station_alpha": 2.0},
            1: {2: 1.0},
            "station_alpha": {2: 0.2},
            2: {},
        }
        res = dijkstra_all(graph, 0)

        self.assertIn(0, res)
        self.assertIn(1, res)
        self.assertIn("station_alpha", res)
        self.assertIn(2, res)
        # 0 -> station_alpha -> 2 is 2.2, vs 0 -> 1 -> 2 is 2.5
        self.assertAlmostEqual(res[2].cost, 2.2)
        self.assertEqual(res[2].path, [0, "station_alpha", 2])

    def test_negative_edge_weights(self) -> None:
        """Verify dijkstra_all raises ValueError when encountering a negative edge."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "A": {"B": -3.0},
            "B": {},
        }
        with self.assertRaises(ValueError) as ctx:
            dijkstra_all(graph, "A")
        self.assertIn("Negative edge weight", str(ctx.exception))

    def test_missing_source_and_empty_graph(self) -> None:
        """Verify empty graph and missing source return an empty dictionary safely."""
        self.assertEqual(dijkstra_all({}, "A"), {})
        graph: Dict[NodeId, Dict[NodeId, float]] = {"B": {"C": 1.0}, "C": {}}
        self.assertEqual(dijkstra_all(graph, "MISSING"), {})

    def test_input_graph_remains_unchanged(self) -> None:
        """Verify the caller's graph is not mutated by dijkstra_all."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "A": {"B": 1.0, "C": 3.0},
            "B": {"C": 1.0},
            "C": {},
        }
        backup = copy.deepcopy(graph)
        dijkstra_all(graph, "A")
        self.assertEqual(graph, backup)

    def test_consistency_with_dijkstra_shortest_path(self) -> None:
        """Verify dijkstra_all and dijkstra_shortest_path produce identical costs and valid paths."""
        graph: Dict[NodeId, Dict[NodeId, float]] = {
            "Origin": {"A": 2.0, "B": 5.0, "C": 10.0},
            "A": {"B": 1.0, "D": 7.0},
            "B": {"C": 2.0, "D": 3.0},
            "C": {"D": 1.0},
            "D": {},
            "ISOLATED": {},
        }
        all_results = dijkstra_all(graph, "Origin")

        # Check all reachable nodes
        for node in ["Origin", "A", "B", "C", "D"]:
            self.assertIn(node, all_results)
            single_result = dijkstra_shortest_path(graph, "Origin", node)
            self.assertEqual(all_results[node].cost, single_result.cost)
            self.assertEqual(all_results[node].path, single_result.path)

        # Check unreachable node consistency
        single_isolated = dijkstra_shortest_path(graph, "Origin", "ISOLATED")
        self.assertNotIn("ISOLATED", all_results)
        self.assertIsNone(single_isolated.path)
        self.assertTrue(math.isinf(single_isolated.cost))


if __name__ == "__main__":
    unittest.main()
