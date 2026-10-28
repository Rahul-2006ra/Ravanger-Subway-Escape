"""Unit tests for the candidate opportunity evaluation and action selection module."""

import math
import unittest

from src.strategy.evaluator import (
    CandidateOpportunity,
    calculate_opportunity_score,
    score_opportunity,
    select_best_opportunity,
)


class TestEvaluator(unittest.TestCase):
    """Test suite for calculate_opportunity_score and select_best_opportunity."""

    def test_known_score(self) -> None:
        """Verify score equals: reward - travel - deposit - risk - urgency - carrying_at_risk."""
        # 100 - 10 - 15 - 5 - 2 - 8 = 60.0
        score = calculate_opportunity_score(
            estimated_reward=100.0,
            travel_cost=10.0,
            deposit_cost=15.0,
            risk_penalty=5.0,
            urgency_penalty=2.0,
            carrying_value_at_risk=8.0,
        )
        self.assertEqual(score, 60.0)

    def test_zero_values(self) -> None:
        """Verify all zero inputs yield a 0.0 score."""
        score = calculate_opportunity_score(0, 0, 0, 0, 0, 0)
        self.assertEqual(score, 0.0)

    def test_net_negative_score(self) -> None:
        """Verify score can be negative when costs and penalties outweigh reward."""
        score = calculate_opportunity_score(
            estimated_reward=20.0,
            travel_cost=25.0,
            deposit_cost=10.0,
            risk_penalty=5.0,
            urgency_penalty=0.0,
            carrying_value_at_risk=0.0,
        )
        self.assertEqual(score, -20.0)

    def test_monotonic_reward_increase(self) -> None:
        """Verify increasing estimated_reward strictly increases score."""
        base_costs = dict(
            travel_cost=10.0,
            deposit_cost=10.0,
            risk_penalty=5.0,
            urgency_penalty=1.0,
            carrying_value_at_risk=2.0,
        )
        rewards = [10.0, 20.0, 50.0, 100.0, 500.0]
        scores = [calculate_opportunity_score(r, **base_costs) for r in rewards]

        for i in range(len(scores) - 1):
            self.assertLess(
                scores[i],
                scores[i + 1],
                f"Monotonicity violated: reward {rewards[i]} -> {scores[i]}, reward {rewards[i+1]} -> {scores[i+1]}",
            )

    def test_monotonic_penalty_increase(self) -> None:
        """Verify increasing any cost/penalty parameter strictly decreases score."""
        params = [
            "travel_cost",
            "deposit_cost",
            "risk_penalty",
            "urgency_penalty",
            "carrying_value_at_risk",
        ]

        for param in params:
            with self.subTest(increasing_param=param):
                kwargs = {
                    "estimated_reward": 200.0,
                    "travel_cost": 10.0,
                    "deposit_cost": 10.0,
                    "risk_penalty": 10.0,
                    "urgency_penalty": 5.0,
                    "carrying_value_at_risk": 5.0,
                }
                # Baseline
                score_low = calculate_opportunity_score(**kwargs)
                # Increase tested param
                kwargs[param] += 50.0
                score_high = calculate_opportunity_score(**kwargs)

                self.assertGreater(
                    score_low,
                    score_high,
                    f"Increasing {param} failed to reduce score.",
                )

    def test_input_validation_negative_values(self) -> None:
        """Verify negative values raise ValueError for each input parameter."""
        params = [
            "estimated_reward",
            "travel_cost",
            "deposit_cost",
            "risk_penalty",
            "urgency_penalty",
            "carrying_value_at_risk",
        ]

        for param in params:
            with self.subTest(negative_param=param):
                kwargs = {p: 10.0 for p in params}
                kwargs[param] = -1.0
                with self.assertRaises(ValueError) as ctx:
                    calculate_opportunity_score(**kwargs)
                self.assertIn("must be non-negative", str(ctx.exception))

    def test_input_validation_nan_and_inf(self) -> None:
        """Verify NaN, +inf, -inf raise ValueError for each input parameter."""
        params = [
            "estimated_reward",
            "travel_cost",
            "deposit_cost",
            "risk_penalty",
            "urgency_penalty",
            "carrying_value_at_risk",
        ]
        bad_numbers = [float("nan"), float("inf"), float("-inf")]

        for param in params:
            for bad in bad_numbers:
                with self.subTest(param=param, bad_val=bad):
                    kwargs = {p: 10.0 for p in params}
                    kwargs[param] = bad
                    with self.assertRaises(ValueError) as ctx:
                        calculate_opportunity_score(**kwargs)
                    self.assertIn("must be a finite real number", str(ctx.exception))

    def test_input_validation_types_and_booleans(self) -> None:
        """Verify non-numeric types and booleans raise TypeError."""
        params = [
            "estimated_reward",
            "travel_cost",
            "deposit_cost",
            "risk_penalty",
            "urgency_penalty",
            "carrying_value_at_risk",
        ]
        bad_types = [True, False, "100", None, [10.0]]

        for param in params:
            for bad in bad_types:
                with self.subTest(param=param, bad_val=bad):
                    kwargs = {p: 10.0 for p in params}
                    kwargs[param] = bad
                    with self.assertRaises(TypeError):
                        calculate_opportunity_score(**kwargs)

    def test_select_best_opportunity_empty_collection(self) -> None:
        """Verify selecting from empty collection returns None."""
        self.assertIsNone(select_best_opportunity([]))
        self.assertIsNone(select_best_opportunity(()))

    def test_select_best_opportunity_distinct_scores(self) -> None:
        """Verify candidate with highest score is selected."""
        cand_a = CandidateOpportunity("A", 100.0, 10.0, 5.0, 2.0, 1.0, 0.0)  # score: 82.0
        cand_b = CandidateOpportunity("B", 150.0, 20.0, 10.0, 5.0, 5.0, 10.0)  # score: 100.0
        cand_c = CandidateOpportunity("C", 80.0, 5.0, 5.0, 0.0, 0.0, 0.0)  # score: 70.0

        best = select_best_opportunity([cand_a, cand_b, cand_c])
        self.assertEqual(best, cand_b)
        self.assertEqual(score_opportunity(cand_b), 100.0)

    def test_select_best_opportunity_tie_breaking(self) -> None:
        """Verify deterministic tie-breaking: lower travel_cost, then earlier candidate_id."""
        # Both score 100 - 20 = 80, but cand_close has lower travel_cost (5 vs 15)
        cand_far = CandidateOpportunity("Far", 100.0, 15.0, 5.0, 0.0, 0.0, 0.0)  # score 80, travel 15
        cand_close = CandidateOpportunity("Close", 100.0, 5.0, 15.0, 0.0, 0.0, 0.0)  # score 80, travel 5

        best = select_best_opportunity([cand_far, cand_close])
        self.assertEqual(best, cand_close)

        # Equal score AND equal travel_cost: breaks tie by string of candidate_id ("Alpha" < "Beta")
        cand_alpha = CandidateOpportunity("Alpha", 100.0, 10.0, 10.0, 0.0, 0.0, 0.0)
        cand_beta = CandidateOpportunity("Beta", 100.0, 10.0, 10.0, 0.0, 0.0, 0.0)

        # Order independent
        self.assertEqual(select_best_opportunity([cand_beta, cand_alpha]), cand_alpha)
        self.assertEqual(select_best_opportunity([cand_alpha, cand_beta]), cand_alpha)

    def test_select_best_opportunity_invalid_candidate(self) -> None:
        """Verify collection with an invalid candidate raises appropriate exception."""
        valid = CandidateOpportunity("V", 100.0, 10.0, 10.0, 0.0, 0.0, 0.0)
        invalid_type = "not_a_candidate"  # type: ignore[arg-type]

        with self.assertRaises(TypeError):
            select_best_opportunity([valid, invalid_type])  # type: ignore[list-item]

    def test_select_best_opportunity_float_precision_tie_breaking(self) -> None:
        """Verify candidates with scores differing by float epsilon (< 1e-12) properly invoke tie-breakers."""
        # cand1 has score 100.0, travel_cost 10.0
        # cand2 has score 100.0 + 1e-14 (within float precision noise), but lower travel_cost 4.0
        # Evaluator should consider them equal on score and select cand2 due to lower travel_cost
        cand1 = CandidateOpportunity("C1", 100.0, 10.0, 0.0, 0.0, 0.0, 0.0)
        cand2 = CandidateOpportunity("C2", 100.0 + 1e-14, 4.0, 0.0, 0.0, 0.0, 0.0)

        best = select_best_opportunity([cand1, cand2])
        self.assertEqual(best, cand2)


if __name__ == "__main__":
    unittest.main()
