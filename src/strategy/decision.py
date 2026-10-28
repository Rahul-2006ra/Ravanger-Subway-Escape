"""Provisional single-runner decision engine.

This module coordinates tactical decision-making by comparing candidate actions:
- COLLECT: Collect money co-located at the runner's current node.
- DEPOSIT: Bank carried capital at a safehouse node.
- MOVE_TO_MONEY: Navigate toward a money opportunity.
- MOVE_TO_SAFEHOUSE: Navigate toward a safehouse to bank carried capital.
- HOLD: Remain at the current station.

Status:
    Provisional. This module operates strictly on mathematical abstractions and
    explicit inputs. It does not bind to external game-state JSON schemas,
    unverified police behavior, or speculative scoring coefficients.
"""

from __future__ import annotations

from enum import Enum
import math
from typing import Any, NamedTuple, Optional, Sequence, Tuple, Union

from src.strategy.money import calculate_exponential_decay
from src.strategy.trip import TripEvaluationResult, evaluate_complete_trip

NodeId = Union[str, int]
Numeric = Union[int, float]


class ActionType(str, Enum):
    """Supported conceptual action archetypes."""

    COLLECT = "COLLECT"
    DEPOSIT = "DEPOSIT"
    MOVE_TO_MONEY = "MOVE_TO_MONEY"
    MOVE_TO_SAFEHOUSE = "MOVE_TO_SAFEHOUSE"
    HOLD = "HOLD"


# Relative preference order when two candidates share identical benefit, cost, and duration
ACTION_PRIORITY = {
    ActionType.DEPOSIT: 5,
    ActionType.COLLECT: 4,
    ActionType.MOVE_TO_SAFEHOUSE: 3,
    ActionType.MOVE_TO_MONEY: 2,
    ActionType.HOLD: 1,
}


class CandidateDecision(NamedTuple):
    """Encapsulates a fully evaluated candidate decision.

    Attributes:
        action_type: Conceptual action category (COLLECT, DEPOSIT, MOVE_TO_MONEY, MOVE_TO_SAFEHOUSE, HOLD).
        target_node: Ultimate destination node of the action (or current node for local actions).
        next_node: Immediate next station to traverse on this tick (or current node for local actions).
        expected_net_benefit: Expected capital banked at a safehouse resulting from this decision.
        route_cost: Path traversal cost (from graph weights; separate from clock ticks).
        duration_ticks: Clock ticks required to complete the action.
        risk_estimate: Probability of capture or hazard index associated with this move.
        candidate_id: Unique string identifier used for logging and deterministic tie-breaking.
        trip_details: Optional underlying TripEvaluationResult if this was a complete trip.
    """

    action_type: ActionType
    target_node: Optional[NodeId]
    next_node: Optional[NodeId]
    expected_net_benefit: float
    route_cost: float
    duration_ticks: float
    risk_estimate: float
    candidate_id: str
    trip_details: Optional[TripEvaluationResult] = None


def validate_decision_inputs(
    expected_net_benefit: Numeric,
    route_cost: Numeric,
    duration_ticks: Numeric,
    risk_estimate: Numeric,
) -> None:
    """Validate core numeric fields for a candidate decision.

    Raises:
        TypeError: If any field is non-numeric or boolean.
        ValueError: If any field is non-finite, if costs/durations are negative,
                    or if risk_estimate is outside [0.0, 1.0].
    """
    params = [
        ("expected_net_benefit", expected_net_benefit),
        ("route_cost", route_cost),
        ("duration_ticks", duration_ticks),
        ("risk_estimate", risk_estimate),
    ]

    for name, val in params:
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise TypeError(f"{name} must be a numeric int or float, got {type(val).__name__}")
        if not math.isfinite(val):
            raise ValueError(f"{name} must be a finite real number, got {val}")

    if expected_net_benefit < 0:
        raise ValueError(f"expected_net_benefit must be non-negative (>= 0), got {expected_net_benefit}")
    if route_cost < 0:
        raise ValueError(f"route_cost must be non-negative (>= 0), got {route_cost}")
    if duration_ticks < 0:
        raise ValueError(f"duration_ticks must be non-negative (>= 0), got {duration_ticks}")
    if not (0.0 <= risk_estimate <= 1.0):
        raise ValueError(f"risk_estimate must lie within [0.0, 1.0], got {risk_estimate}")


def evaluate_money_opportunity(
    runner_node: NodeId,
    money_node: NodeId,
    safehouse_node: NodeId,
    opportunity_nominal_value: Numeric,
    initial_carried_capital: Numeric,
    leg1_path: Optional[Sequence[NodeId]],
    leg1_route_cost: Numeric,
    leg1_duration_ticks: Numeric,
    leg2_route_cost: Numeric,
    leg2_duration_ticks: Numeric,
    remaining_ticks: Numeric,
    leg1_capture_prob: Numeric,
    leg2_capture_prob: Numeric,
    map_decay_rate: Numeric,
    carried_decay_rate: Optional[Numeric] = None,
    candidate_id: Optional[str] = None,
) -> CandidateDecision:
    """Evaluate navigating to a money opportunity as a complete round-trip to safehouse.

    Uses evaluate_complete_trip from src.strategy.trip to compute exact decay and
    risk-weighted expected deposit.
    """
    # Validate node identifiers
    for node_name, node_val in [("runner_node", runner_node), ("money_node", money_node), ("safehouse_node", safehouse_node)]:
        if isinstance(node_val, bool) or not isinstance(node_val, (str, int)):
            raise TypeError(f"{node_name} must be a str or int, got {type(node_val).__name__}")

    cid = candidate_id or f"money_{money_node}_safe_{safehouse_node}"

    # Configure default carried decay rate
    actual_carried_decay_rate = map_decay_rate if carried_decay_rate is None else carried_decay_rate

    # Validate numeric parameters upfront
    numeric_params = [
        ("opportunity_nominal_value", opportunity_nominal_value),
        ("initial_carried_capital", initial_carried_capital),
        ("leg1_duration_ticks", leg1_duration_ticks),
        ("leg2_duration_ticks", leg2_duration_ticks),
        ("remaining_ticks", remaining_ticks),
        ("map_decay_rate", map_decay_rate),
        ("carried_decay_rate", actual_carried_decay_rate),
    ]
    for name, val in numeric_params:
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise TypeError(f"{name} must be a numeric int or float, got {type(val).__name__}")
        if not math.isfinite(val):
            raise ValueError(f"{name} must be a finite real number, got {val}")
        if val < 0:
            raise ValueError(f"{name} must be non-negative (>= 0), got {val}")

    # Validate route costs (can be inf, but not NaN or negative)
    for cost_name, cost_val in [("leg1_route_cost", leg1_route_cost), ("leg2_route_cost", leg2_route_cost)]:
        if not isinstance(cost_val, (int, float)) or isinstance(cost_val, bool):
            raise TypeError(f"{cost_name} must be a numeric int or float, got {type(cost_val).__name__}")
        if math.isnan(cost_val):
            raise ValueError(f"{cost_name} cannot be NaN")
        if cost_val < 0:
            raise ValueError(f"{cost_name} must be non-negative (>= 0), got {cost_val}")

    # Validate capture probabilities
    for prob_name, prob in [("leg1_capture_prob", leg1_capture_prob), ("leg2_capture_prob", leg2_capture_prob)]:
        if not isinstance(prob, (int, float)) or isinstance(prob, bool):
            raise TypeError(f"{prob_name} must be a numeric int or float, got {type(prob).__name__}")
        if not math.isfinite(prob):
            raise ValueError(f"{prob_name} must be a finite real number, got {prob}")
        if not (0.0 <= prob <= 1.0):
            raise ValueError(f"{prob_name} must lie within [0.0, 1.0], got {prob}")

    # Check if target is reachable
    if leg1_path is None or math.isinf(leg1_route_cost) or math.isinf(leg2_route_cost):
        return CandidateDecision(
            action_type=ActionType.MOVE_TO_MONEY if runner_node != money_node else ActionType.COLLECT,
            target_node=money_node,
            next_node=runner_node,
            expected_net_benefit=0.0,
            route_cost=float("inf") if leg1_path is None else float(leg1_route_cost),
            duration_ticks=float(leg1_duration_ticks),
            risk_estimate=1.0,
            candidate_id=cid,
            trip_details=None,
        )

    trip_res = evaluate_complete_trip(
        initial_carried_capital=initial_carried_capital,
        opportunity_nominal_value=opportunity_nominal_value,
        leg1_duration_ticks=leg1_duration_ticks,
        leg2_duration_ticks=leg2_duration_ticks,
        remaining_ticks=remaining_ticks,
        leg1_capture_prob=leg1_capture_prob,
        leg2_capture_prob=leg2_capture_prob,
        map_decay_rate=map_decay_rate,
        carried_decay_rate=carried_decay_rate,
    )

    # Determine action type and next hop
    if runner_node == money_node:
        action_type = ActionType.COLLECT
        next_node = runner_node
    else:
        action_type = ActionType.MOVE_TO_MONEY
        next_node = leg1_path[1] if len(leg1_path) > 1 else money_node

    return CandidateDecision(
        action_type=action_type,
        target_node=money_node,
        next_node=next_node,
        expected_net_benefit=trip_res.expected_deposited_capital,
        route_cost=float(leg1_route_cost),
        duration_ticks=float(leg1_duration_ticks),
        risk_estimate=float(leg1_capture_prob),
        candidate_id=cid,
        trip_details=trip_res,
    )


def evaluate_deposit_opportunity(
    runner_node: NodeId,
    safehouse_node: NodeId,
    carried_capital: Numeric,
    path: Optional[Sequence[NodeId]],
    route_cost: Numeric,
    duration_ticks: Numeric,
    remaining_ticks: Numeric,
    capture_prob: Numeric,
    carried_decay_rate: Numeric,
    candidate_id: Optional[str] = None,
) -> CandidateDecision:
    """Evaluate moving to or executing a deposit at a safehouse."""
    cid = candidate_id or f"safehouse_{safehouse_node}"

    # Validate node identifiers
    for node_name, node_val in [("runner_node", runner_node), ("safehouse_node", safehouse_node)]:
        if isinstance(node_val, bool) or not isinstance(node_val, (str, int)):
            raise TypeError(f"{node_name} must be a str or int, got {type(node_val).__name__}")

    # Validate numeric parameters upfront
    numeric_params = [
        ("carried_capital", carried_capital),
        ("duration_ticks", duration_ticks),
        ("remaining_ticks", remaining_ticks),
        ("carried_decay_rate", carried_decay_rate),
    ]
    for name, val in numeric_params:
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise TypeError(f"{name} must be a numeric int or float, got {type(val).__name__}")
        if not math.isfinite(val):
            raise ValueError(f"{name} must be a finite real number, got {val}")
        if val < 0:
            raise ValueError(f"{name} must be non-negative (>= 0), got {val}")

    # Validate route_cost (can be inf, but not NaN or negative)
    if not isinstance(route_cost, (int, float)) or isinstance(route_cost, bool):
        raise TypeError(f"route_cost must be a numeric int or float, got {type(route_cost).__name__}")
    if math.isnan(route_cost):
        raise ValueError("route_cost cannot be NaN")
    if route_cost < 0:
        raise ValueError(f"route_cost must be non-negative (>= 0), got {route_cost}")

    # Validate capture_prob
    if not isinstance(capture_prob, (int, float)) or isinstance(capture_prob, bool):
        raise TypeError(f"capture_prob must be a numeric int or float, got {type(capture_prob).__name__}")
    if not math.isfinite(capture_prob):
        raise ValueError(f"capture_prob must be a finite real number, got {capture_prob}")
    if not (0.0 <= capture_prob <= 1.0):
        raise ValueError(f"capture_prob must lie within [0.0, 1.0], got {capture_prob}")

    # Local deposit case: runner is already at the safehouse
    if runner_node == safehouse_node:
        return CandidateDecision(
            action_type=ActionType.DEPOSIT,
            target_node=safehouse_node,
            next_node=runner_node,
            expected_net_benefit=float(carried_capital),
            route_cost=0.0,
            duration_ticks=0.0,
            risk_estimate=0.0,
            candidate_id=cid,
            trip_details=None,
        )

    # Remote safehouse transit
    if path is None or math.isinf(route_cost) or float(duration_ticks) > float(remaining_ticks):
        return CandidateDecision(
            action_type=ActionType.MOVE_TO_SAFEHOUSE,
            target_node=safehouse_node,
            next_node=runner_node,
            expected_net_benefit=0.0,
            route_cost=float("inf") if path is None else float(route_cost),
            duration_ticks=float(duration_ticks),
            risk_estimate=1.0 if path is None else float(capture_prob),
            candidate_id=cid,
            trip_details=None,
        )

    # Decayed capital upon arrival at safehouse
    decayed_capital = calculate_exponential_decay(
        initial_value=carried_capital,
        decay_rate=carried_decay_rate,
        elapsed_time=duration_ticks,
    )
    expected_deposited = (1.0 - float(capture_prob)) * decayed_capital
    next_node = path[1] if len(path) > 1 else safehouse_node

    return CandidateDecision(
        action_type=ActionType.MOVE_TO_SAFEHOUSE,
        target_node=safehouse_node,
        next_node=next_node,
        expected_net_benefit=expected_deposited,
        route_cost=float(route_cost),
        duration_ticks=float(duration_ticks),
        risk_estimate=float(capture_prob),
        candidate_id=cid,
        trip_details=None,
    )


def evaluate_hold_opportunity(
    runner_node: NodeId,
    risk_estimate: Numeric = 0.0,
    candidate_id: Optional[str] = None,
) -> CandidateDecision:
    """Evaluate holding position at current station."""
    if isinstance(runner_node, bool) or not isinstance(runner_node, (str, int)):
        raise TypeError(f"runner_node must be a str or int, got {type(runner_node).__name__}")

    cid = candidate_id or f"hold_{runner_node}"
    validate_decision_inputs(
        expected_net_benefit=0.0,
        route_cost=0.0,
        duration_ticks=0.0,
        risk_estimate=risk_estimate,
    )
    return CandidateDecision(
        action_type=ActionType.HOLD,
        target_node=runner_node,
        next_node=runner_node,
        expected_net_benefit=0.0,
        route_cost=0.0,
        duration_ticks=0.0,
        risk_estimate=float(risk_estimate),
        candidate_id=cid,
        trip_details=None,
    )


def select_best_decision(
    candidates: Sequence[CandidateDecision],
) -> Optional[CandidateDecision]:
    """Select the candidate decision with the highest expected net benefit.

    Deterministic Tie-Breaking Rules:
        1. Primary: Highest expected_net_benefit (descending).
        2. Secondary: Lower route_cost (ascending, preferring efficient graph paths).
        3. Tertiary: Lower duration_ticks (ascending, preferring faster clock completion).
        4. Quaternary: Action category priority (DEPOSIT > COLLECT > MOVE_TO_SAFEHOUSE > MOVE_TO_MONEY > HOLD).
        5. Quinary: String representation of candidate_id (lexicographically ascending).

    Args:
        candidates: Sequence of CandidateDecision instances.

    Returns:
        Optional[CandidateDecision]: The optimal candidate, or None if candidates is empty.

    Raises:
        TypeError: If any candidate is not a CandidateDecision or has invalid field types.
        ValueError: If any candidate has non-finite values or out-of-bounds fields.
    """
    if not candidates:
        return None

    best_candidate: Optional[CandidateDecision] = None
    best_key: Optional[Tuple[float, float, float, int, str]] = None

    for item in candidates:
        if not isinstance(item, CandidateDecision):
            raise TypeError(f"All candidates must be CandidateDecision instances, got {type(item).__name__}")

        # Validate item
        validate_decision_inputs(
            expected_net_benefit=item.expected_net_benefit,
            route_cost=0.0 if math.isinf(item.route_cost) else item.route_cost,
            duration_ticks=item.duration_ticks,
            risk_estimate=item.risk_estimate,
        )

        action_prio = ACTION_PRIORITY.get(item.action_type, 0)

        # Tie-breaker key:
        # (benefit, -route_cost, -duration_ticks, action_priority, -candidate_id_str)
        # Using negation where smaller values are preferred.
        item_key = (
            float(item.expected_net_benefit),
            -float(item.route_cost),
            -float(item.duration_ticks),
            action_prio,
            str(item.candidate_id),
        )

        if best_key is None:
            best_candidate = item
            best_key = item_key
        else:
            # 1. Primary: expected_net_benefit
            if not math.isclose(item_key[0], best_key[0], abs_tol=1e-12):
                if item_key[0] > best_key[0]:
                    best_candidate = item
                    best_key = item_key
            else:
                # 2. Secondary: route_cost (larger -cost is preferred)
                if not math.isclose(item_key[1], best_key[1], abs_tol=1e-12):
                    if item_key[1] > best_key[1]:
                        best_candidate = item
                        best_key = item_key
                else:
                    # 3. Tertiary: duration_ticks (larger -duration is preferred)
                    if not math.isclose(item_key[2], best_key[2], abs_tol=1e-12):
                        if item_key[2] > best_key[2]:
                            best_candidate = item
                            best_key = item_key
                    else:
                        # 4. Quaternary: action category priority
                        if item_key[3] != best_key[3]:
                            if item_key[3] > best_key[3]:
                                best_candidate = item
                                best_key = item_key
                        else:
                            # 5. Quinary: candidate_id (lexicographically smaller is preferred)
                            if item_key[4] < best_key[4]:
                                best_candidate = item
                                best_key = item_key

    return best_candidate
