"""Unit tests for the provisional single-runner decision engine."""

import math
import unittest

from src.strategy.decision import (
    ActionType,
    CandidateDecision,
    evaluate_deposit_opportunity,
    evaluate_hold_opportunity,
    evaluate_money_opportunity,
    select_best_decision,
    validate_decision_inputs,
)


class TestDecisionEngine(unittest.TestCase):
    """Test suite for decision candidate evaluation and optimal selection."""

    def test_empty_candidate_set(self) -> None:
        """Verify select_best_decision returns None when given an empty sequence."""
        self.assertIsNone(select_best_decision([]))
        self.assertIsNone(select_best_decision(()))

    def test_candidate_selection_distinct_benefits(self) -> None:
        """Verify candidate with highest expected net benefit is selected."""
        cand1 = CandidateDecision(ActionType.MOVE_TO_MONEY, "M1", "N1", 50.0, 3.0, 3.0, 0.1, "c1")
        cand2 = CandidateDecision(ActionType.MOVE_TO_MONEY, "M2", "N2", 120.0, 5.0, 5.0, 0.1, "c2")
        cand3 = CandidateDecision(ActionType.HOLD, "S0", "S0", 0.0, 0.0, 0.0, 0.0, "c3")

        best = select_best_decision([cand1, cand2, cand3])
        self.assertEqual(best, cand2)

    def test_deadline_infeasible_trip_rejected(self) -> None:
        """Verify deadline-infeasible trips receive 0.0 benefit and a feasible alternative is chosen."""
        # Infeasible trip: 15 ticks leg1 + 10 ticks leg2 = 25 ticks > 10 remaining ticks
        infeasible = evaluate_money_opportunity(
            runner_node="A",
            money_node="FAR_MONEY",
            safehouse_node="S1",
            opportunity_nominal_value=1000.0,
            initial_carried_capital=0.0,
            leg1_path=["A", "B", "FAR_MONEY"],
            leg1_route_cost=15.0,
            leg1_duration_ticks=15.0,
            leg2_route_cost=10.0,
            leg2_duration_ticks=10.0,
            remaining_ticks=10.0,  # Insufficient budget!
            leg1_capture_prob=0.0,
            leg2_capture_prob=0.0,
            map_decay_rate=0.01,
            candidate_id="far_infeasible",
        )
        self.assertEqual(infeasible.expected_net_benefit, 0.0)

        # Feasible trip: 2 ticks leg1 + 2 ticks leg2 = 4 ticks <= 10 remaining ticks
        feasible = evaluate_money_opportunity(
            runner_node="A",
            money_node="NEAR_MONEY",
            safehouse_node="S1",
            opportunity_nominal_value=100.0,
            initial_carried_capital=0.0,
            leg1_path=["A", "NEAR_MONEY"],
            leg1_route_cost=2.0,
            leg1_duration_ticks=2.0,
            leg2_route_cost=2.0,
            leg2_duration_ticks=2.0,
            remaining_ticks=10.0,
            leg1_capture_prob=0.0,
            leg2_capture_prob=0.0,
            map_decay_rate=0.01,
            candidate_id="near_feasible",
        )
        self.assertGreater(feasible.expected_net_benefit, 0.0)

        best = select_best_decision([infeasible, feasible])
        self.assertEqual(best, feasible)

    def test_sensible_deposit_versus_collection_choices(self) -> None:
        """Verify sensible choices: banking large carried wealth vs collecting small risky money."""
        # Scenario A: Runner carries 500.0 at a safehouse node.
        # Option 1: Deposit immediately (net benefit: 500.0, cost: 0, duration: 0)
        dep_option = evaluate_deposit_opportunity(
            runner_node="SAFEHOUSE",
            safehouse_node="SAFEHOUSE",
            carried_capital=500.0,
            path=["SAFEHOUSE"],
            route_cost=0.0,
            duration_ticks=0.0,
            remaining_ticks=50.0,
            capture_prob=0.0,
            carried_decay_rate=0.01,
        )
        self.assertEqual(dep_option.action_type, ActionType.DEPOSIT)
        self.assertEqual(dep_option.expected_net_benefit, 500.0)

        # Option 2: Leave safehouse to chase a 20.0 coin drop with 0.1 capture risk
        money_option = evaluate_money_opportunity(
            runner_node="SAFEHOUSE",
            money_node="RISKY_DROP",
            safehouse_node="SAFEHOUSE",
            opportunity_nominal_value=20.0,
            initial_carried_capital=500.0,
            leg1_path=["SAFEHOUSE", "RISKY_DROP"],
            leg1_route_cost=3.0,
            leg1_duration_ticks=3.0,
            leg2_route_cost=3.0,
            leg2_duration_ticks=3.0,
            remaining_ticks=50.0,
            leg1_capture_prob=0.1,
            leg2_capture_prob=0.1,
            map_decay_rate=0.01,
        )

        # Decision engine must choose DEPOSIT to secure the 500.0 rather than risking it for 20.0
        best = select_best_decision([dep_option, money_option])
        self.assertEqual(best, dep_option)

        # Scenario B: Runner carries 0.0 at a safehouse node.
        # Now deposit yields 0.0, while chasing money yields positive expected deposit.
        dep_empty = evaluate_deposit_opportunity(
            runner_node="SAFEHOUSE",
            safehouse_node="SAFEHOUSE",
            carried_capital=0.0,
            path=["SAFEHOUSE"],
            route_cost=0.0,
            duration_ticks=0.0,
            remaining_ticks=50.0,
            capture_prob=0.0,
            carried_decay_rate=0.01,
        )
        best_b = select_best_decision([dep_empty, money_option])
        self.assertEqual(best_b, money_option)

    def test_unreachable_target_handling(self) -> None:
        """Verify opportunities with no path or infinite cost yield 0.0 benefit."""
        unreachable = evaluate_money_opportunity(
            runner_node="A",
            money_node="ISOLATED",
            safehouse_node="S1",
            opportunity_nominal_value=100.0,
            initial_carried_capital=0.0,
            leg1_path=None,  # No path exists
            leg1_route_cost=float("inf"),
            leg1_duration_ticks=0.0,
            leg2_route_cost=2.0,
            leg2_duration_ticks=2.0,
            remaining_ticks=20.0,
            leg1_capture_prob=0.0,
            leg2_capture_prob=0.0,
            map_decay_rate=0.0,
        )
        self.assertEqual(unreachable.expected_net_benefit, 0.0)
        self.assertTrue(math.isinf(unreachable.route_cost))

    def test_deterministic_tie_breaking(self) -> None:
        """Verify deterministic multi-level tie-breaking hierarchy."""
        # 1. Secondary tie-breaker: lower route_cost (when benefits are identical)
        c_high_cost = CandidateDecision(ActionType.MOVE_TO_MONEY, "M1", "N1", 50.0, 10.0, 2.0, 0.0, "c_high_cost")
        c_low_cost = CandidateDecision(ActionType.MOVE_TO_MONEY, "M2", "N2", 50.0, 4.0, 2.0, 0.0, "c_low_cost")
        self.assertEqual(select_best_decision([c_high_cost, c_low_cost]), c_low_cost)

        # 2. Tertiary tie-breaker: lower duration_ticks (when benefit and cost are identical)
        c_slow = CandidateDecision(ActionType.MOVE_TO_MONEY, "M1", "N1", 50.0, 5.0, 8.0, 0.0, "c_slow")
        c_fast = CandidateDecision(ActionType.MOVE_TO_MONEY, "M2", "N2", 50.0, 5.0, 3.0, 0.0, "c_fast")
        self.assertEqual(select_best_decision([c_slow, c_fast]), c_fast)

        # 3. Quaternary tie-breaker: action priority (DEPOSIT > COLLECT > MOVE_TO_SAFEHOUSE)
        c_collect = CandidateDecision(ActionType.COLLECT, "X", "X", 50.0, 0.0, 0.0, 0.0, "c_collect")
        c_deposit = CandidateDecision(ActionType.DEPOSIT, "X", "X", 50.0, 0.0, 0.0, 0.0, "c_deposit")
        self.assertEqual(select_best_decision([c_collect, c_deposit]), c_deposit)

        # 4. Quinary tie-breaker: candidate_id lexicographically ascending ("alpha" < "beta")
        c_alpha = CandidateDecision(ActionType.HOLD, "H", "H", 0.0, 0.0, 0.0, 0.0, "alpha")
        c_beta = CandidateDecision(ActionType.HOLD, "H", "H", 0.0, 0.0, 0.0, 0.0, "beta")
        self.assertEqual(select_best_decision([c_beta, c_alpha]), c_alpha)

    def test_invalid_inputs_rejected(self) -> None:
        """Verify booleans and invalid values raise TypeError or ValueError."""
        # evaluate_hold_opportunity rejects boolean risk
        with self.assertRaises(TypeError):
            evaluate_hold_opportunity(runner_node="A", risk_estimate=True)  # type: ignore[arg-type]

        # In select_best_decision, passing non-CandidateDecision types
        with self.assertRaises(TypeError):
            select_best_decision(["not_a_candidate"])  # type: ignore[list-item]

        # select_best_decision rejects candidate with boolean fields
        bad_bool = CandidateDecision(ActionType.HOLD, "H", "H", True, 0.0, 0.0, 0.0, "bad")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            select_best_decision([bad_bool])

        # Candidate with negative cost
        bad_cand = CandidateDecision(ActionType.HOLD, "H", "H", 0.0, -5.0, 0.0, 0.0, "bad_cost")
        with self.assertRaises(ValueError):
            select_best_decision([bad_cand])

    def test_collect_at_current_node(self) -> None:
        """Verify co-located money generates COLLECT action with next_node = current node."""
        col = evaluate_money_opportunity(
            runner_node="NODE_5",
            money_node="NODE_5",
            safehouse_node="S1",
            opportunity_nominal_value=80.0,
            initial_carried_capital=0.0,
            leg1_path=["NODE_5"],
            leg1_route_cost=0.0,
            leg1_duration_ticks=0.0,
            leg2_route_cost=4.0,
            leg2_duration_ticks=4.0,
            remaining_ticks=30.0,
            leg1_capture_prob=0.0,
            leg2_capture_prob=0.0,
            map_decay_rate=0.01,
        )
        self.assertEqual(col.action_type, ActionType.COLLECT)
        self.assertEqual(col.target_node, "NODE_5")
        self.assertEqual(col.next_node, "NODE_5")
        self.assertGreater(col.expected_net_benefit, 0.0)

    def test_move_to_safehouse_with_carried_capital(self) -> None:
        """Verify moving to safehouse discounts carried capital for transit decay and risk."""
        move_safe = evaluate_deposit_opportunity(
            runner_node="STATION_1",
            safehouse_node="SAFEHOUSE_A",
            carried_capital=100.0,
            path=["STATION_1", "INTERMEDIATE", "SAFEHOUSE_A"],
            route_cost=2.0,
            duration_ticks=2.0,
            remaining_ticks=20.0,
            capture_prob=0.1,
            carried_decay_rate=0.05,
        )
        self.assertEqual(move_safe.action_type, ActionType.MOVE_TO_SAFEHOUSE)
        self.assertEqual(move_safe.next_node, "INTERMEDIATE")

        expected_decayed = 100.0 * math.exp(-0.05 * 2.0)
        expected_deposit = 0.9 * expected_decayed
        self.assertAlmostEqual(move_safe.expected_net_benefit, expected_deposit, places=9)

    def test_evaluate_hold_opportunity(self) -> None:
        """Verify evaluate_hold_opportunity creates valid HOLD candidate."""
        hold = evaluate_hold_opportunity(runner_node="A", risk_estimate=0.05)
        self.assertEqual(hold.action_type, ActionType.HOLD)
        self.assertEqual(hold.expected_net_benefit, 0.0)
        self.assertEqual(hold.next_node, "A")
        self.assertEqual(hold.risk_estimate, 0.05)

    def test_negative_expected_benefit_rejected(self) -> None:
        """Verify negative expected_net_benefit is rejected in validation and decision selection."""
        with self.assertRaises(ValueError):
            validate_decision_inputs(expected_net_benefit=-1.0, route_cost=0.0, duration_ticks=0.0, risk_estimate=0.0)

        bad_cand = CandidateDecision(ActionType.HOLD, "H", "H", -50.0, 0.0, 0.0, 0.0, "bad_benefit")
        with self.assertRaises(ValueError):
            select_best_decision([bad_cand])

    def test_evaluate_deposit_opportunity_input_validation(self) -> None:
        """Verify evaluate_deposit_opportunity validates all parameters across all scenarios."""
        # 1. Negative carried capital rejected even at co-located safehouse
        with self.assertRaises(ValueError):
            evaluate_deposit_opportunity("S", "S", carried_capital=-10.0, path=["S"], route_cost=0.0,
                                         duration_ticks=0.0, remaining_ticks=10.0, capture_prob=0.0, carried_decay_rate=0.01)

        # 2. Boolean carried capital rejected
        with self.assertRaises(TypeError):
            evaluate_deposit_opportunity("S", "S", carried_capital=True, path=["S"], route_cost=0.0,  # type: ignore[arg-type]
                                         duration_ticks=0.0, remaining_ticks=10.0, capture_prob=0.0, carried_decay_rate=0.01)

        # 3. Negative remaining ticks rejected even when duration_ticks exceeds it
        with self.assertRaises(ValueError):
            evaluate_deposit_opportunity("A", "S", carried_capital=100.0, path=["A", "S"], route_cost=10.0,
                                         duration_ticks=20.0, remaining_ticks=-5.0, capture_prob=0.0, carried_decay_rate=0.01)

        # 4. Out-of-bounds capture probability rejected
        with self.assertRaises(ValueError):
            evaluate_deposit_opportunity("A", "S", carried_capital=100.0, path=["A", "S"], route_cost=10.0,
                                         duration_ticks=2.0, remaining_ticks=10.0, capture_prob=1.5, carried_decay_rate=0.01)

    def test_evaluate_money_opportunity_input_validation_even_if_unreachable(self) -> None:
        """Verify evaluate_money_opportunity rejects invalid inputs even when target is unreachable."""
        # Target has no path (path=None), but negative duration is passed
        with self.assertRaises(ValueError):
            evaluate_money_opportunity(
                runner_node="A", money_node="U", safehouse_node="S",
                opportunity_nominal_value=100.0, initial_carried_capital=0.0,
                leg1_path=None, leg1_route_cost=float("inf"), leg1_duration_ticks=-5.0,  # Invalid duration!
                leg2_route_cost=1.0, leg2_duration_ticks=1.0, remaining_ticks=10.0,
                leg1_capture_prob=0.0, leg2_capture_prob=0.0, map_decay_rate=0.01,
            )

        # Target has path, but capture prob > 1.0 even when leg2_route_cost is infinite
        with self.assertRaises(ValueError):
            evaluate_money_opportunity(
                runner_node="A", money_node="U", safehouse_node="S",
                opportunity_nominal_value=100.0, initial_carried_capital=0.0,
                leg1_path=["A", "U"], leg1_route_cost=1.0, leg1_duration_ticks=1.0,
                leg2_route_cost=float("inf"), leg2_duration_ticks=1.0, remaining_ticks=10.0,
                leg1_capture_prob=1.2, leg2_capture_prob=0.0, map_decay_rate=0.01,  # Invalid prob!
            )

    def test_synthetic_scenario_deadline_infeasible_versus_safe_deposit(self) -> None:
        """Verify that an infeasible distant high-reward trip cannot beat a feasible safehouse deposit."""
        # Runner carries 300.0, safehouse S is 2 ticks away. Deadline is 10 ticks.
        # Direct safehouse transit: 2 ticks <= 10 ticks (feasible). Expected deposit ~279.36
        safe_option = evaluate_deposit_opportunity(
            runner_node="R",
            safehouse_node="S",
            carried_capital=300.0,
            path=["R", "N1", "S"],
            route_cost=2.0,
            duration_ticks=2.0,
            remaining_ticks=10.0,
            capture_prob=0.05,
            carried_decay_rate=0.01,
            candidate_id="deposit_S",
        )
        self.assertGreater(safe_option.expected_net_benefit, 270.0)

        # Distant money drop: huge reward 1000.0, but trip is 8 + 8 = 16 ticks > 10 remaining ticks!
        infeasible_money = evaluate_money_opportunity(
            runner_node="R",
            money_node="DISTANT_M",
            safehouse_node="S",
            opportunity_nominal_value=1000.0,
            initial_carried_capital=300.0,
            leg1_path=["R", "D1", "DISTANT_M"],
            leg1_route_cost=8.0,
            leg1_duration_ticks=8.0,
            leg2_route_cost=8.0,
            leg2_duration_ticks=8.0,
            remaining_ticks=10.0,
            leg1_capture_prob=0.20,
            leg2_capture_prob=0.25,
            map_decay_rate=0.01,
            candidate_id="distant_money",
        )
        # Even though nominal reward is 1000.0 vs 300.0, deadline infeasibility yields 0.0
        self.assertEqual(infeasible_money.expected_net_benefit, 0.0)

        best = select_best_decision([safe_option, infeasible_money])
        self.assertEqual(best, safe_option)

    def test_synthetic_scenario_reward_justified_versus_threat_overwhelming(self) -> None:
        """Verify that risk-adjusted expected deposit correctly weighs threat to carried wealth."""
        # Remaining ticks: 20 ticks (both are feasible)
        # Safehouse deposit: delivers 300 * exp(-0.02) * 0.95 ~ 279.36
        safe_option = evaluate_deposit_opportunity(
            runner_node="R",
            safehouse_node="S",
            carried_capital=300.0,
            path=["R", "N1", "S"],
            route_cost=2.0,
            duration_ticks=2.0,
            remaining_ticks=20.0,
            capture_prob=0.05,
            carried_decay_rate=0.01,
            candidate_id="safe_dep",
        )

        # Case 1: Moderate risk (p1=0.20, p2=0.25, S=0.60).
        # Complete trip delivers ~1107.79 * 0.60 ~ 664.67 > 279.36 -> Choose MONEY
        moderate_money = evaluate_money_opportunity(
            runner_node="R",
            money_node="DISTANT_M",
            safehouse_node="S",
            opportunity_nominal_value=1000.0,
            initial_carried_capital=300.0,
            leg1_path=["R", "D1", "DISTANT_M"],
            leg1_route_cost=8.0,
            leg1_duration_ticks=8.0,
            leg2_route_cost=8.0,
            leg2_duration_ticks=8.0,
            remaining_ticks=20.0,
            leg1_capture_prob=0.20,
            leg2_capture_prob=0.25,
            map_decay_rate=0.01,
            candidate_id="moderate_money",
        )
        self.assertEqual(select_best_decision([safe_option, moderate_money]), moderate_money)

        # Case 2: Severe threat (p1=0.75, p2=0.25, S=0.1875).
        # Complete trip delivers ~1107.79 * 0.1875 ~ 207.71 < 279.36 -> Choose SAFEHOUSE to protect wealth
        severe_money = evaluate_money_opportunity(
            runner_node="R",
            money_node="DISTANT_M",
            safehouse_node="S",
            opportunity_nominal_value=1000.0,
            initial_carried_capital=300.0,
            leg1_path=["R", "D1", "DISTANT_M"],
            leg1_route_cost=8.0,
            leg1_duration_ticks=8.0,
            leg2_route_cost=8.0,
            leg2_duration_ticks=8.0,
            remaining_ticks=20.0,
            leg1_capture_prob=0.75,  # Severe threat!
            leg2_capture_prob=0.25,
            map_decay_rate=0.01,
            candidate_id="severe_money",
        )
        self.assertEqual(select_best_decision([safe_option, severe_money]), safe_option)

        # Case 3: Same severe threat (p1=0.75), but carried capital is 0.
        # Now safehouse delivers 0.0, while money trip delivers ~159.78 > 0.0 -> Choose MONEY
        empty_safe = evaluate_deposit_opportunity(
            runner_node="R", safehouse_node="S", carried_capital=0.0, path=["R", "N1", "S"],
            route_cost=2.0, duration_ticks=2.0, remaining_ticks=20.0, capture_prob=0.05, carried_decay_rate=0.01,
        )
        empty_severe_money = evaluate_money_opportunity(
            runner_node="R", money_node="DISTANT_M", safehouse_node="S",
            opportunity_nominal_value=1000.0, initial_carried_capital=0.0,
            leg1_path=["R", "D1", "DISTANT_M"], leg1_route_cost=8.0, leg1_duration_ticks=8.0,
            leg2_route_cost=8.0, leg2_duration_ticks=8.0, remaining_ticks=20.0,
            leg1_capture_prob=0.75, leg2_capture_prob=0.25, map_decay_rate=0.01,
        )
        self.assertEqual(select_best_decision([empty_safe, empty_severe_money]), empty_severe_money)

    def test_consistent_comparison_all_five_action_types(self) -> None:
        """Verify COLLECT, DEPOSIT, MOVE_TO_MONEY, MOVE_TO_SAFEHOUSE, HOLD compare consistently."""
        # Let candidate net benefits be strictly ordered:
        # COLLECT (300) > MOVE_TO_MONEY (200) > DEPOSIT (100) > MOVE_TO_SAFEHOUSE (50) > HOLD (0)
        c_hold = evaluate_hold_opportunity("R", candidate_id="c_hold")
        c_move_safe = CandidateDecision(ActionType.MOVE_TO_SAFEHOUSE, "S", "N1", 50.0, 1.0, 1.0, 0.0, "c_move_safe")
        c_deposit = CandidateDecision(ActionType.DEPOSIT, "S", "S", 100.0, 0.0, 0.0, 0.0, "c_deposit")
        c_move_money = CandidateDecision(ActionType.MOVE_TO_MONEY, "M", "N2", 200.0, 2.0, 2.0, 0.0, "c_move_money")
        c_collect = CandidateDecision(ActionType.COLLECT, "M", "M", 300.0, 0.0, 0.0, 0.0, "c_collect")

        all_actions = [c_hold, c_move_safe, c_deposit, c_move_money, c_collect]
        best = select_best_decision(all_actions)
        self.assertEqual(best, c_collect)

        # Without collect, move_money wins
        self.assertEqual(select_best_decision([c_hold, c_move_safe, c_deposit, c_move_money]), c_move_money)

        # Without move_money, deposit wins
        self.assertEqual(select_best_decision([c_hold, c_move_safe, c_deposit]), c_deposit)

        # Without deposit, move_safe wins
        self.assertEqual(select_best_decision([c_hold, c_move_safe]), c_move_safe)

        # Only hold remains
        self.assertEqual(select_best_decision([c_hold]), c_hold)

    def test_node_id_type_validation_rejects_booleans(self) -> None:
        """Verify node IDs reject booleans and non-string/non-int types."""
        # evaluate_money_opportunity rejects boolean node IDs
        with self.assertRaises(TypeError):
            evaluate_money_opportunity(
                runner_node=True, money_node="M", safehouse_node="S",  # type: ignore[arg-type]
                opportunity_nominal_value=100.0, initial_carried_capital=0.0,
                leg1_path=["M"], leg1_route_cost=0.0, leg1_duration_ticks=0.0,
                leg2_route_cost=1.0, leg2_duration_ticks=1.0, remaining_ticks=10.0,
                leg1_capture_prob=0.0, leg2_capture_prob=0.0, map_decay_rate=0.01,
            )

        # evaluate_deposit_opportunity rejects boolean node IDs
        with self.assertRaises(TypeError):
            evaluate_deposit_opportunity(
                runner_node="A", safehouse_node=False, carried_capital=100.0,  # type: ignore[arg-type]
                path=["A", "S"], route_cost=1.0, duration_ticks=1.0, remaining_ticks=10.0,
                capture_prob=0.0, carried_decay_rate=0.01,
            )

        # evaluate_hold_opportunity rejects boolean node IDs
        with self.assertRaises(TypeError):
            evaluate_hold_opportunity(runner_node=True)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
