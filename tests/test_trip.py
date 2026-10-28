"""Unit tests for the complete-trip feasibility and expected deposit calculator."""

import math
import unittest

from src.strategy.trip import TripEvaluationResult, evaluate_complete_trip


class TestTripEvaluation(unittest.TestCase):
    """Test suite for evaluate_complete_trip function."""

    def test_feasible_trip_zero_capture_risk(self) -> None:
        """Verify feasible trip with zero capture risk delivers full decayed capital."""
        # Leg 1: 5 ticks, Leg 2: 5 ticks, Remaining: 20 ticks
        # Opp value: 100.0, Carried: 50.0, Decay rate: 0.0
        res = evaluate_complete_trip(
            initial_carried_capital=50.0,
            opportunity_nominal_value=100.0,
            leg1_duration_ticks=5,
            leg2_duration_ticks=5,
            remaining_ticks=20,
            leg1_capture_prob=0.0,
            leg2_capture_prob=0.0,
            map_decay_rate=0.0,
        )

        self.assertTrue(res.is_feasible)
        self.assertEqual(res.total_duration_ticks, 10.0)
        self.assertEqual(res.overall_survival_prob, 1.0)
        self.assertEqual(res.collected_money_at_opportunity, 100.0)
        self.assertEqual(res.carried_money_after_leg1, 50.0)
        self.assertEqual(res.total_capital_at_safehouse, 150.0)
        self.assertEqual(res.expected_deposited_capital, 150.0)

    def test_trip_exceeds_remaining_tick_budget(self) -> None:
        """Verify trip exceeding remaining ticks is marked infeasible with 0.0 expected deposit."""
        # Leg 1: 15 ticks, Leg 2: 10 ticks = 25 ticks > 20 remaining ticks
        res = evaluate_complete_trip(
            initial_carried_capital=0.0,
            opportunity_nominal_value=500.0,
            leg1_duration_ticks=15,
            leg2_duration_ticks=10,
            remaining_ticks=20,
            leg1_capture_prob=0.0,
            leg2_capture_prob=0.0,
            map_decay_rate=0.01,
        )

        self.assertFalse(res.is_feasible)
        self.assertEqual(res.total_duration_ticks, 25.0)
        self.assertEqual(res.remaining_ticks, 20.0)
        self.assertEqual(res.expected_deposited_capital, 0.0)

    def test_zero_travel_durations(self) -> None:
        """Verify zero travel durations experience no decay and 0 total duration."""
        res = evaluate_complete_trip(
            initial_carried_capital=75.0,
            opportunity_nominal_value=25.0,
            leg1_duration_ticks=0,
            leg2_duration_ticks=0,
            remaining_ticks=10,
            leg1_capture_prob=0.0,
            leg2_capture_prob=0.0,
            map_decay_rate=0.05,
        )

        self.assertTrue(res.is_feasible)
        self.assertEqual(res.total_duration_ticks, 0.0)
        self.assertEqual(res.collected_money_at_opportunity, 25.0)
        self.assertEqual(res.carried_money_after_leg1, 75.0)
        self.assertEqual(res.total_capital_at_safehouse, 100.0)
        self.assertEqual(res.expected_deposited_capital, 100.0)

    def test_zero_starting_inventory_and_zero_opportunity(self) -> None:
        """Verify zero initial capital and zero opportunity value yields 0.0 deposit."""
        res = evaluate_complete_trip(
            initial_carried_capital=0.0,
            opportunity_nominal_value=0.0,
            leg1_duration_ticks=5,
            leg2_duration_ticks=5,
            remaining_ticks=20,
            leg1_capture_prob=0.1,
            leg2_capture_prob=0.1,
            map_decay_rate=0.02,
        )

        self.assertTrue(res.is_feasible)
        self.assertEqual(res.collected_money_at_opportunity, 0.0)
        self.assertEqual(res.carried_money_after_leg1, 0.0)
        self.assertEqual(res.total_capital_at_safehouse, 0.0)
        self.assertEqual(res.expected_deposited_capital, 0.0)

    def test_capture_probabilities_boundaries_zero_and_one(self) -> None:
        """Verify boundary probabilities: p=1 causes 0 expected deposit; p=0 gives full delivery."""
        # Certain capture on Leg 1 (p1 = 1.0)
        res_p1_one = evaluate_complete_trip(
            initial_carried_capital=50.0,
            opportunity_nominal_value=100.0,
            leg1_duration_ticks=2,
            leg2_duration_ticks=2,
            remaining_ticks=10,
            leg1_capture_prob=1.0,
            leg2_capture_prob=0.0,
            map_decay_rate=0.0,
        )
        self.assertEqual(res_p1_one.overall_survival_prob, 0.0)
        self.assertEqual(res_p1_one.expected_deposited_capital, 0.0)

        # Certain capture on Leg 2 (p2 = 1.0)
        res_p2_one = evaluate_complete_trip(
            initial_carried_capital=50.0,
            opportunity_nominal_value=100.0,
            leg1_duration_ticks=2,
            leg2_duration_ticks=2,
            remaining_ticks=10,
            leg1_capture_prob=0.0,
            leg2_capture_prob=1.0,
            map_decay_rate=0.0,
        )
        self.assertEqual(res_p2_one.overall_survival_prob, 0.0)
        self.assertEqual(res_p2_one.expected_deposited_capital, 0.0)

    def test_money_decay_across_both_legs(self) -> None:
        """Verify exponential decay is calculated accurately across both legs."""
        # Opp: 100.0 decaying over Leg 1 (t=10, rate=0.05) -> 100 * exp(-0.5)
        # Carried: 200.0 decaying over Leg 1 (t=10, rate=0.05) -> 200 * exp(-0.5)
        # Total at start of Leg 2 = 300 * exp(-0.5)
        # Decaying over Leg 2 (t=10, rate=0.05) -> 300 * exp(-0.5) * exp(-0.5) = 300 * exp(-1.0)
        lam = 0.05
        t1, t2 = 10, 10
        res = evaluate_complete_trip(
            initial_carried_capital=200.0,
            opportunity_nominal_value=100.0,
            leg1_duration_ticks=t1,
            leg2_duration_ticks=t2,
            remaining_ticks=50,
            leg1_capture_prob=0.0,
            leg2_capture_prob=0.0,
            map_decay_rate=lam,
        )

        expected_opp_at_m = 100.0 * math.exp(-lam * t1)
        expected_carried_at_m = 200.0 * math.exp(-lam * t1)
        expected_total_safehouse = (expected_opp_at_m + expected_carried_at_m) * math.exp(-lam * t2)

        self.assertAlmostEqual(res.collected_money_at_opportunity, expected_opp_at_m, places=9)
        self.assertAlmostEqual(res.carried_money_after_leg1, expected_carried_at_m, places=9)
        self.assertAlmostEqual(res.total_capital_at_safehouse, expected_total_safehouse, places=9)
        self.assertAlmostEqual(res.expected_deposited_capital, expected_total_safehouse, places=9)

    def test_monotonicity_increasing_capture_probabilities(self) -> None:
        """Verify increasing capture probability on either leg strictly decreases expected deposit."""
        base_kwargs = dict(
            initial_carried_capital=100.0,
            opportunity_nominal_value=100.0,
            leg1_duration_ticks=4,
            leg2_duration_ticks=4,
            remaining_ticks=20,
            map_decay_rate=0.01,
        )

        # Vary leg1_capture_prob
        probs = [0.0, 0.1, 0.25, 0.5, 0.8, 1.0]
        leg1_deposits = [
            evaluate_complete_trip(leg1_capture_prob=p, leg2_capture_prob=0.1, **base_kwargs).expected_deposited_capital
            for p in probs
        ]
        for i in range(len(leg1_deposits) - 1):
            self.assertGreater(
                leg1_deposits[i],
                leg1_deposits[i + 1],
                f"Increasing leg1_capture_prob failed to strictly decrease expected deposit at step {i}",
            )

        # Vary leg2_capture_prob
        leg2_deposits = [
            evaluate_complete_trip(leg1_capture_prob=0.1, leg2_capture_prob=p, **base_kwargs).expected_deposited_capital
            for p in probs
        ]
        for i in range(len(leg2_deposits) - 1):
            self.assertGreater(
                leg2_deposits[i],
                leg2_deposits[i + 1],
                f"Increasing leg2_capture_prob failed to strictly decrease expected deposit at step {i}",
            )

    def test_handling_carried_vs_uncollected_money_exposure(self) -> None:
        """Verify uncollected opportunity money is not exposed during Leg 1 traversal."""
        # Consider two runs with identical opportunity value (100.0) but differing Leg 1 capture risk
        # Opportunity collected at node M is 100.0 regardless of Leg 1 risk
        res_low_risk = evaluate_complete_trip(
            initial_carried_capital=0.0,
            opportunity_nominal_value=100.0,
            leg1_duration_ticks=0,
            leg2_duration_ticks=0,
            remaining_ticks=10,
            leg1_capture_prob=0.1,
            leg2_capture_prob=0.0,
            map_decay_rate=0.0,
        )
        res_high_risk = evaluate_complete_trip(
            initial_carried_capital=0.0,
            opportunity_nominal_value=100.0,
            leg1_duration_ticks=0,
            leg2_duration_ticks=0,
            remaining_ticks=10,
            leg1_capture_prob=0.9,
            leg2_capture_prob=0.0,
            map_decay_rate=0.0,
        )

        # Value collected at destination is unaffected by Leg 1 risk
        self.assertEqual(res_low_risk.collected_money_at_opportunity, 100.0)
        self.assertEqual(res_high_risk.collected_money_at_opportunity, 100.0)

        # But expected deposit scales with Leg 1 survival probability
        self.assertAlmostEqual(res_low_risk.expected_deposited_capital, 90.0)
        self.assertAlmostEqual(res_high_risk.expected_deposited_capital, 10.0)

    def test_input_validation_negative_values_and_durations(self) -> None:
        """Verify negative durations, capital, and remaining ticks raise ValueError."""
        valid_kwargs = dict(
            initial_carried_capital=10.0,
            opportunity_nominal_value=20.0,
            leg1_duration_ticks=3.0,
            leg2_duration_ticks=3.0,
            remaining_ticks=10.0,
            leg1_capture_prob=0.1,
            leg2_capture_prob=0.1,
            map_decay_rate=0.01,
        )

        for param in ["initial_carried_capital", "opportunity_nominal_value", "leg1_duration_ticks", "leg2_duration_ticks", "remaining_ticks", "map_decay_rate"]:
            with self.subTest(negative_param=param):
                kwargs = dict(valid_kwargs)
                kwargs[param] = -1.0
                with self.assertRaises(ValueError) as ctx:
                    evaluate_complete_trip(**kwargs)
                self.assertIn("must be non-negative", str(ctx.exception))

    def test_input_validation_probabilities_out_of_bounds(self) -> None:
        """Verify probabilities outside [0.0, 1.0] raise ValueError."""
        valid_kwargs = dict(
            initial_carried_capital=10.0,
            opportunity_nominal_value=20.0,
            leg1_duration_ticks=3,
            leg2_duration_ticks=3,
            remaining_ticks=10,
            map_decay_rate=0.01,
        )

        bad_probs = [-0.1, 1.0001, 2.0, -10.0]
        for prob in bad_probs:
            with self.subTest(bad_prob=prob):
                with self.assertRaises(ValueError):
                    evaluate_complete_trip(leg1_capture_prob=prob, leg2_capture_prob=0.1, **valid_kwargs)
                with self.assertRaises(ValueError):
                    evaluate_complete_trip(leg1_capture_prob=0.1, leg2_capture_prob=prob, **valid_kwargs)

    def test_input_validation_nan_and_inf(self) -> None:
        """Verify NaN, +inf, -inf raise ValueError across all parameters."""
        valid_kwargs = dict(
            initial_carried_capital=10.0,
            opportunity_nominal_value=20.0,
            leg1_duration_ticks=3.0,
            leg2_duration_ticks=3.0,
            remaining_ticks=10.0,
            leg1_capture_prob=0.1,
            leg2_capture_prob=0.1,
            map_decay_rate=0.01,
        )
        non_finites = [float("nan"), float("inf"), float("-inf")]

        for param in valid_kwargs:
            for bad in non_finites:
                with self.subTest(param=param, bad_val=bad):
                    kwargs = dict(valid_kwargs)
                    kwargs[param] = bad
                    with self.assertRaises(ValueError):
                        evaluate_complete_trip(**kwargs)

    def test_input_validation_types_and_booleans(self) -> None:
        """Verify booleans and non-numeric types raise TypeError."""
        valid_kwargs = dict(
            initial_carried_capital=10.0,
            opportunity_nominal_value=20.0,
            leg1_duration_ticks=3.0,
            leg2_duration_ticks=3.0,
            remaining_ticks=10.0,
            leg1_capture_prob=0.1,
            leg2_capture_prob=0.1,
            map_decay_rate=0.01,
        )
        bad_types = [True, False, "10", None, [1.0]]

        for param in valid_kwargs:
            for bad in bad_types:
                with self.subTest(param=param, bad_type=type(bad).__name__):
                    kwargs = dict(valid_kwargs)
                    kwargs[param] = bad
                    with self.assertRaises(TypeError):
                        evaluate_complete_trip(**kwargs)


if __name__ == "__main__":
    unittest.main()
