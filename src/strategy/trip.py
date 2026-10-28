"""Trip evaluation and complete-journey expected deposit calculator.

This module models a complete two-leg opportunity cycle:
    Current Position --(Leg 1: travel)--> Money Opportunity --(Leg 2: travel)--> Safehouse

It calculates trip feasibility against the 300-tick game clock, models decay
along each leg, and computes the risk-weighted expected capital successfully
deposited at the safehouse under explicit survival probabilities.
"""

from __future__ import annotations

import math
from typing import NamedTuple, Optional, Union

from src.strategy.money import calculate_exponential_decay

Numeric = Union[int, float]


class TripEvaluationResult(NamedTuple):
    """Immutable outcome of a complete-trip feasibility and deposit evaluation.

    Attributes:
        is_feasible: True if (leg1_duration_ticks + leg2_duration_ticks) <= remaining_ticks.
        total_duration_ticks: Total clock time required to complete both legs.
        remaining_ticks: Time budget available when the trip evaluation was performed.
        expected_deposited_capital: Expected value of capital successfully banked at safehouse
            (0.0 if the trip is infeasible or capture probability is 1.0).
        collected_money_at_opportunity: Value of money collected at destination after Leg 1 decay.
        carried_money_after_leg1: Initial carried inventory remaining after Leg 1 decay.
        total_capital_at_safehouse: Nominal capital delivered to safehouse if runner survives both legs.
        overall_survival_prob: Compound probability of surviving both legs: (1 - p1) * (1 - p2).
    """

    is_feasible: bool
    total_duration_ticks: float
    remaining_ticks: float
    expected_deposited_capital: float
    collected_money_at_opportunity: float
    carried_money_after_leg1: float
    total_capital_at_safehouse: float
    overall_survival_prob: float


def evaluate_complete_trip(
    initial_carried_capital: Numeric,
    opportunity_nominal_value: Numeric,
    leg1_duration_ticks: Numeric,
    leg2_duration_ticks: Numeric,
    remaining_ticks: Numeric,
    leg1_capture_prob: Numeric,
    leg2_capture_prob: Numeric,
    map_decay_rate: Numeric,
    carried_decay_rate: Optional[Numeric] = None,
    opportunity_decay_duration: Optional[Numeric] = None,
) -> TripEvaluationResult:
    """Evaluate a complete two-leg trip from current position to money opportunity to safehouse.

    Trip Sequence:
        Leg 1: Current position to money opportunity (duration: leg1_duration_ticks).
               Runner carries initial_carried_capital (exposed to leg1_capture_prob).
               Opportunity money decays over opportunity_decay_duration.
        Pickup: Runner collects decayed opportunity money and combines it with surviving
                carried inventory.
        Leg 2: Opportunity to safehouse (duration: leg2_duration_ticks).
               Runner carries total combined capital (exposed to leg2_capture_prob).
               All carried money decays over leg2_duration_ticks.
        Deposit: Surviving capital is deposited at the safehouse.

    Mathematical Model & Assumptions:
        1. Feasibility:
           Total ticks = leg1_duration_ticks + leg2_duration_ticks.
           The trip is feasible if and only if total_ticks <= remaining_ticks.
           For infeasible trips, is_feasible=False and expected_deposited_capital=0.0.
        2. Exposure Separation:
           Money at the opportunity node is NOT exposed to capture during Leg 1.
           If capture occurs during Leg 1, the runner never collects the opportunity money.
        3. Conditional Independence:
           Leg survival probabilities s1 = (1 - leg1_capture_prob) and
           s2 = (1 - leg2_capture_prob) assume conditional independence between legs.
           Overall survival probability S = s1 * s2.
        4. Expectation Calculation:
           Expected deposited capital E = S * total_capital_at_safehouse.
           Survival probability accounts directly for capture outcomes; expected losses
           are not subtracted a second time.

    Validation & Error Handling:
        - Booleans and non-numeric types raise TypeError.
        - Non-finite numbers (NaN, inf, -inf) raise ValueError.
        - Negative values for capital, durations, remaining ticks, or decay rates raise ValueError.
        - Capture probabilities must lie within [0.0, 1.0]; outside values raise ValueError.

    Args:
        initial_carried_capital: Non-negative capital held before starting Leg 1.
        opportunity_nominal_value: Non-negative nominal value of money opportunity.
        leg1_duration_ticks: Non-negative ticks required to traverse Leg 1.
        leg2_duration_ticks: Non-negative ticks required to traverse Leg 2.
        remaining_ticks: Non-negative total ticks remaining in the match.
        leg1_capture_prob: Probability of capture during Leg 1, in [0.0, 1.0].
        leg2_capture_prob: Probability of capture during Leg 2, in [0.0, 1.0].
        map_decay_rate: Non-negative exponential decay parameter for opportunity money.
        carried_decay_rate: Non-negative decay rate for carried inventory (defaults to map_decay_rate).
        opportunity_decay_duration: Non-negative elapsed decay time for opportunity money
            (defaults to leg1_duration_ticks).

    Returns:
        TripEvaluationResult: Documented immutable named tuple.

    Raises:
        TypeError: If any argument is non-numeric or boolean.
        ValueError: If any numeric argument is non-finite, negative, or if probabilities
                    fall outside [0.0, 1.0].
    """
    # Configure default parameters
    actual_carried_decay_rate = map_decay_rate if carried_decay_rate is None else carried_decay_rate
    actual_opp_decay_duration = leg1_duration_ticks if opportunity_decay_duration is None else opportunity_decay_duration

    # General parameter validation list
    params = [
        ("initial_carried_capital", initial_carried_capital),
        ("opportunity_nominal_value", opportunity_nominal_value),
        ("leg1_duration_ticks", leg1_duration_ticks),
        ("leg2_duration_ticks", leg2_duration_ticks),
        ("remaining_ticks", remaining_ticks),
        ("map_decay_rate", map_decay_rate),
        ("carried_decay_rate", actual_carried_decay_rate),
        ("opportunity_decay_duration", actual_opp_decay_duration),
    ]

    for name, val in params:
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise TypeError(f"{name} must be a numeric int or float, got {type(val).__name__}")
        if not math.isfinite(val):
            raise ValueError(f"{name} must be a finite real number, got {val}")
        if val < 0:
            raise ValueError(f"{name} must be non-negative (>= 0), got {val}")

    # Probability validation [0.0, 1.0]
    for prob_name, prob in [("leg1_capture_prob", leg1_capture_prob), ("leg2_capture_prob", leg2_capture_prob)]:
        if not isinstance(prob, (int, float)) or isinstance(prob, bool):
            raise TypeError(f"{prob_name} must be a numeric int or float, got {type(prob).__name__}")
        if not math.isfinite(prob):
            raise ValueError(f"{prob_name} must be a finite real number, got {prob}")
        if not (0.0 <= prob <= 1.0):
            raise ValueError(f"{prob_name} must lie within [0.0, 1.0], got {prob}")

    # Compute duration and feasibility
    total_duration = float(leg1_duration_ticks) + float(leg2_duration_ticks)
    is_feasible = total_duration <= float(remaining_ticks)

    # Leg 1 Decay Calculations:
    # 1. Opportunity money decays over opportunity_decay_duration
    collected_money = calculate_exponential_decay(
        initial_value=opportunity_nominal_value,
        decay_rate=map_decay_rate,
        elapsed_time=actual_opp_decay_duration,
    )

    # 2. Initial carried capital decays over leg1_duration_ticks
    carried_after_leg1 = calculate_exponential_decay(
        initial_value=initial_carried_capital,
        decay_rate=actual_carried_decay_rate,
        elapsed_time=leg1_duration_ticks,
    )

    # Intermediate combined capital at start of Leg 2
    total_carried_leg2 = carried_after_leg1 + collected_money

    # Leg 2 Decay: combined capital decays over leg2_duration_ticks
    total_at_safehouse = calculate_exponential_decay(
        initial_value=total_carried_leg2,
        decay_rate=actual_carried_decay_rate,
        elapsed_time=leg2_duration_ticks,
    )

    # Survival probabilities
    s1 = 1.0 - float(leg1_capture_prob)
    s2 = 1.0 - float(leg2_capture_prob)
    overall_survival = s1 * s2

    # Expected deposited capital:
    # If feasible: compound survival probability * delivered capital
    # If infeasible: 0.0 (infeasible trips cannot bank capital before match end)
    if is_feasible:
        expected_deposit = overall_survival * total_at_safehouse
    else:
        expected_deposit = 0.0

    return TripEvaluationResult(
        is_feasible=is_feasible,
        total_duration_ticks=total_duration,
        remaining_ticks=float(remaining_ticks),
        expected_deposited_capital=expected_deposit,
        collected_money_at_opportunity=collected_money,
        carried_money_after_leg1=carried_after_leg1,
        total_capital_at_safehouse=total_at_safehouse,
        overall_survival_prob=overall_survival,
    )
