"""Opportunity evaluation and candidate action scoring module.

This module provides a deterministic, standalone heuristic evaluator to score and
rank competing game opportunities (such as candidate money drops or routes).
"""

from __future__ import annotations

import math
from typing import Any, Iterable, List, NamedTuple, Optional, Sequence, Tuple, Union

Numeric = Union[int, float]


class CandidateOpportunity(NamedTuple):
    """Encapsulates the cost and reward parameters of a candidate game action.

    Attributes:
        candidate_id: Unique identifier for the candidate (string or integer).
        estimated_reward: Expected money reward (decay-adjusted if applicable).
        travel_cost: Estimated transit cost/hops to reach the opportunity.
        deposit_cost: Estimated transit cost to reach a safehouse after collection.
        risk_penalty: Heuristic penalty representing chaser threat / intercept risk.
        urgency_penalty: Penalty for delays or potential expiry.
        carrying_value_at_risk: Capital currently carried that could be forfeited on capture.
    """

    candidate_id: Union[str, int]
    estimated_reward: float
    travel_cost: float
    deposit_cost: float
    risk_penalty: float
    urgency_penalty: float
    carrying_value_at_risk: float


def calculate_opportunity_score(
    estimated_reward: Numeric,
    travel_cost: Numeric,
    deposit_cost: Numeric,
    risk_penalty: Numeric,
    urgency_penalty: Numeric,
    carrying_value_at_risk: Numeric,
) -> float:
    """Compute the heuristic priority score for a candidate opportunity.

    Baseline Formula:
        score = estimated_reward
              - travel_cost
              - deposit_cost
              - risk_penalty
              - urgency_penalty
              - carrying_value_at_risk

    Dimensional & Strategic Limitations:
        - This is a provisional, baseline 1:1 subtractive heuristic.
        - Currency units (capital reward, money at risk) and transit units (ticks, hops)
          are not inherently commensurable without empirical scaling coefficients.
        - The resulting score can be negative if estimated costs and penalties outweigh
          the anticipated reward.
        - Does not represent a guaranteed winning strategy; weights will require calibration
          once the full match economics and official schemas are confirmed.

    Validation & Error Handling:
        - All 6 arguments must be numeric int or float. Booleans raise TypeError.
        - All arguments must be finite real numbers. NaN, +inf, and -inf raise ValueError.
        - All arguments must be non-negative (>= 0). Negative values raise ValueError.

    Args:
        estimated_reward: Non-negative reward expectation.
        travel_cost: Non-negative transit cost to target.
        deposit_cost: Non-negative transit cost to subsequent safehouse.
        risk_penalty: Non-negative hazard penalty.
        urgency_penalty: Non-negative delay/expiry penalty.
        carrying_value_at_risk: Non-negative carried capital at risk.

    Returns:
        float: Computed net opportunity score (can be negative).

    Raises:
        TypeError: If any argument is non-numeric or boolean.
        ValueError: If any argument is negative or non-finite.
    """
    params = [
        ("estimated_reward", estimated_reward),
        ("travel_cost", travel_cost),
        ("deposit_cost", deposit_cost),
        ("risk_penalty", risk_penalty),
        ("urgency_penalty", urgency_penalty),
        ("carrying_value_at_risk", carrying_value_at_risk),
    ]

    for name, val in params:
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise TypeError(f"{name} must be a numeric int or float, got {type(val).__name__}")
        if not math.isfinite(val):
            raise ValueError(f"{name} must be a finite real number, got {val}")
        if val < 0:
            raise ValueError(f"{name} must be non-negative (>= 0), got {val}")

    score = (
        float(estimated_reward)
        - float(travel_cost)
        - float(deposit_cost)
        - float(risk_penalty)
        - float(urgency_penalty)
        - float(carrying_value_at_risk)
    )

    return score


def score_opportunity(candidate: CandidateOpportunity) -> float:
    """Calculate the opportunity score directly from a CandidateOpportunity instance.

    Args:
        candidate: CandidateOpportunity data tuple.

    Returns:
        float: Computed opportunity score.

    Raises:
        TypeError: If candidate is not an instance of CandidateOpportunity or has invalid field types.
        ValueError: If any field values are negative or non-finite.
    """
    if not isinstance(candidate, CandidateOpportunity):
        raise TypeError(f"candidate must be a CandidateOpportunity, got {type(candidate).__name__}")

    return calculate_opportunity_score(
        estimated_reward=candidate.estimated_reward,
        travel_cost=candidate.travel_cost,
        deposit_cost=candidate.deposit_cost,
        risk_penalty=candidate.risk_penalty,
        urgency_penalty=candidate.urgency_penalty,
        carrying_value_at_risk=candidate.carrying_value_at_risk,
    )


def select_best_opportunity(
    candidates: Iterable[CandidateOpportunity],
) -> Optional[CandidateOpportunity]:
    """Select the candidate opportunity with the highest score from a collection.

    Deterministic Tie-Breaking Rules:
        1. Primary: Highest opportunity score (descending).
        2. Secondary: Lowest travel_cost (ascending, preferring closer opportunities).
        3. Tertiary: String representation of candidate_id (lexicographically ascending).

    Behavior on Empty Input:
        - If candidates is empty or contains no items, returns None.

    Validation & Error Handling:
        - If any item in candidates is invalid or has non-numeric/negative fields,
          the corresponding exception (TypeError or ValueError) is propagated.

    Args:
        candidates: Iterable collection of CandidateOpportunity objects.

    Returns:
        Optional[CandidateOpportunity]: The highest-scoring candidate, or None if empty.

    Raises:
        TypeError: If any candidate is of invalid type or contains invalid field types.
        ValueError: If any candidate contains non-finite or negative field values.
    """
    best_candidate: Optional[CandidateOpportunity] = None
    best_key: Optional[Tuple[float, float, str]] = None

    for item in candidates:
        score = score_opportunity(item)

        # Tie-breaker key: (score, -travel_cost, -candidate_id_str)
        # Using negated values for secondary/tertiary so max() prefers lower travel_cost and lexicographically earlier ID.
        candidate_key = (
            score,
            -float(item.travel_cost),
            str(item.candidate_id),
        )

        if best_key is None:
            best_candidate = item
            best_key = candidate_key
        else:
            # Compare primary score with tolerance
            if not math.isclose(score, best_key[0], abs_tol=1e-12):
                if score > best_key[0]:
                    best_candidate = item
                    best_key = candidate_key
            else:
                # Primary equal, check secondary: lower travel_cost (larger -travel_cost)
                if not math.isclose(candidate_key[1], best_key[1], abs_tol=1e-12):
                    if candidate_key[1] > best_key[1]:
                        best_candidate = item
                        best_key = candidate_key
                else:
                    # Secondary equal, check tertiary: lexicographically smaller ID
                    if candidate_key[2] < best_key[2]:
                        best_candidate = item
                        best_key = candidate_key

    return best_candidate
