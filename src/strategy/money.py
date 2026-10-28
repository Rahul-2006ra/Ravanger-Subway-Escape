"""Money and value decay calculation utilities.

This module provides standalone mathematical functions to model decay of money
over time using standard exponential decay formulations.
"""

from __future__ import annotations

import math
from typing import Union

Numeric = Union[int, float]


def calculate_exponential_decay(
    initial_value: Numeric,
    decay_rate: Numeric,
    elapsed_time: Numeric,
) -> float:
    """Calculate the remaining money amount under continuous exponential decay.

    Formula:
        M(t) = M0 * exp(-lambda * t)

    Where:
        - M0 is initial_value
        - lambda is decay_rate
        - t is elapsed_time

    Validation & Error Handling:
        - All parameters must be finite real numbers. Inputs of float('nan'),
          float('inf'), or float('-inf') raise ValueError.
        - initial_value must be non-negative (>= 0). Negative values raise ValueError.
        - decay_rate must be non-negative (>= 0). Negative values raise ValueError.
        - elapsed_time must be non-negative (>= 0). Negative values raise ValueError.
        - Non-numeric types raise TypeError.
        - Invalid inputs are strictly rejected and never silently converted.

    Properties:
        - If elapsed_time == 0, returns float(initial_value).
        - If decay_rate == 0, returns float(initial_value).
        - If initial_value == 0, returns 0.0.
        - As elapsed_time -> inf with decay_rate > 0, returns 0.0 safely without underflow errors.

    Args:
        initial_value: Non-negative initial money amount.
        decay_rate: Non-negative decay rate parameter (lambda).
        elapsed_time: Non-negative elapsed time in ticks or seconds (t).

    Returns:
        float: Remaining money value after elapsed_time.

    Raises:
        TypeError: If any argument is not an int or float.
        ValueError: If any argument is non-finite (NaN, inf) or negative (< 0).
    """
    # Type validation
    if not isinstance(initial_value, (int, float)) or isinstance(initial_value, bool):
        raise TypeError(f"initial_value must be a numeric int or float, got {type(initial_value).__name__}")
    if not isinstance(decay_rate, (int, float)) or isinstance(decay_rate, bool):
        raise TypeError(f"decay_rate must be a numeric int or float, got {type(decay_rate).__name__}")
    if not isinstance(elapsed_time, (int, float)) or isinstance(elapsed_time, bool):
        raise TypeError(f"elapsed_time must be a numeric int or float, got {type(elapsed_time).__name__}")

    # Finiteness validation (reject NaN and +/-inf)
    if not math.isfinite(initial_value):
        raise ValueError(f"initial_value must be a finite real number, got {initial_value}")
    if not math.isfinite(decay_rate):
        raise ValueError(f"decay_rate must be a finite real number, got {decay_rate}")
    if not math.isfinite(elapsed_time):
        raise ValueError(f"elapsed_time must be a finite real number, got {elapsed_time}")

    # Non-negativity validation
    if initial_value < 0:
        raise ValueError(f"initial_value must be non-negative (>= 0), got {initial_value}")
    if decay_rate < 0:
        raise ValueError(f"decay_rate must be non-negative (>= 0), got {decay_rate}")
    if elapsed_time < 0:
        raise ValueError(f"elapsed_time must be non-negative (>= 0), got {elapsed_time}")

    # Fast-paths for zero values
    if initial_value == 0:
        return 0.0
    if elapsed_time == 0 or decay_rate == 0:
        return float(initial_value)

    # Exponent is guaranteed to be <= 0 because decay_rate >= 0 and elapsed_time >= 0.
    # For large negative exponents, math.exp underflows safely to 0.0 without OverflowError.
    exponent = -float(decay_rate) * float(elapsed_time)
    decay_factor = math.exp(exponent)

    return float(initial_value) * decay_factor
