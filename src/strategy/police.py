"""Police movement and position estimation utilities.

This module provides standalone mathematical functions for 2D position prediction
using a constant-velocity kinematic model and Euclidean distance calculations.
"""

from __future__ import annotations

import math
from typing import NamedTuple, Sequence, Tuple, Union

Numeric = Union[int, float]


class Point2D(NamedTuple):
    """Immutable representation of a 2D Cartesian coordinate pair.

    Attributes:
        x: X-axis coordinate.
        y: Y-axis coordinate.
    """

    x: float
    y: float


def predict_constant_velocity_position(
    x: Numeric,
    y: Numeric,
    vx: Numeric,
    vy: Numeric,
    elapsed_ticks: Numeric,
) -> Point2D:
    """Predict future 2D position under an unconstrained constant-velocity model.

    Kinematic formula:
        future_x = x + vx * elapsed_ticks
        future_y = y + vy * elapsed_ticks

    Validation & Error Handling:
        - All arguments must be numeric int or float. Booleans and non-numeric types
          raise TypeError.
        - All arguments must be finite real numbers. NaN, +inf, and -inf raise ValueError.
        - elapsed_ticks must be non-negative (>= 0). Negative values raise ValueError.
        - Resulting coordinates are validated to ensure they remain finite real numbers.

    Assumptions & Limitations:
        - Assumes straight-line motion in continuous Euclidean space without obstacles,
          track constraints, friction, or turning acceleration.
        - Serves as a baseline motion model; does not represent official game routing
          or graph-constrained chaser AI until official mechanics are integrated.

    Args:
        x: Current X-coordinate.
        y: Current Y-coordinate.
        vx: Velocity component along X-axis per tick.
        vy: Velocity component along Y-axis per tick.
        elapsed_ticks: Number of ticks elapsed into the future (>= 0).

    Returns:
        Point2D: Predicted (x, y) coordinates.

    Raises:
        TypeError: If any argument is a boolean or non-numeric type.
        ValueError: If any argument is non-finite, if elapsed_ticks < 0,
                    or if the computed coordinates overflow to infinity.
    """
    params = [
        ("x", x),
        ("y", y),
        ("vx", vx),
        ("vy", vy),
        ("elapsed_ticks", elapsed_ticks),
    ]

    for name, val in params:
        # Exclude bool explicitly since isinstance(True, int) is True in Python
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise TypeError(f"{name} must be a numeric int or float, got {type(val).__name__}")
        if not math.isfinite(val):
            raise ValueError(f"{name} must be a finite real number, got {val}")

    if elapsed_ticks < 0:
        raise ValueError(f"elapsed_ticks must be non-negative (>= 0), got {elapsed_ticks}")

    future_x = float(x) + float(vx) * float(elapsed_ticks)
    future_y = float(y) + float(vy) * float(elapsed_ticks)

    if not math.isfinite(future_x) or not math.isfinite(future_y):
        raise ValueError("Predicted coordinates overflowed to non-finite values.")

    return Point2D(x=future_x, y=future_y)


def calculate_euclidean_distance(
    p1: Union[Point2D, Tuple[Numeric, Numeric], Sequence[Numeric]],
    p2: Union[Point2D, Tuple[Numeric, Numeric], Sequence[Numeric]],
) -> float:
    """Calculate the straight-line Euclidean distance between two 2D points.

    Formula:
        dist = sqrt((x2 - x1)^2 + (y2 - y1)^2)

    Validation & Error Handling:
        - Both points must be 2-element indexable sequences (x, y).
        - All coordinates must be numeric (excluding booleans) and finite.
        - Raises TypeError for non-numeric or boolean coordinates.
        - Raises ValueError for invalid point lengths or non-finite coordinates.

    Args:
        p1: First 2D point (x1, y1).
        p2: Second 2D point (x2, y2).

    Returns:
        float: Euclidean distance (always >= 0.0).

    Raises:
        TypeError: If point coordinates are non-numeric or booleans.
        ValueError: If points do not have exactly 2 coordinates or contain NaN/inf.
    """
    for point_name, pt in [("p1", p1), ("p2", p2)]:
        if isinstance(pt, (str, bytes)):
            raise TypeError(f"{point_name} must be a 2-element numeric sequence, got {type(pt).__name__}")

        try:
            length = len(pt)  # type: ignore[arg-type]
        except (TypeError, AttributeError):
            raise TypeError(f"{point_name} must be a 2-element sequence, got {type(pt).__name__}")

        if length != 2:
            raise ValueError(f"{point_name} must contain exactly 2 coordinates, got {length}")

        for idx, coord in enumerate(pt):
            if not isinstance(coord, (int, float)) or isinstance(coord, bool):
                raise TypeError(
                    f"{point_name}[{idx}] must be a numeric int or float, got {type(coord).__name__}"
                )
            if not math.isfinite(coord):
                raise ValueError(f"{point_name}[{idx}] must be a finite real number, got {coord}")

    dx = float(p2[0]) - float(p1[0])
    dy = float(p2[1]) - float(p1[1])

    dist = math.hypot(dx, dy)
    if not math.isfinite(dist):
        raise ValueError("Computed Euclidean distance overflowed to infinity.")

    return dist
