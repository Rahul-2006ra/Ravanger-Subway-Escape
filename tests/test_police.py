"""Unit tests for the police position prediction and distance module."""

import math
import unittest

from src.strategy.police import (
    Point2D,
    calculate_euclidean_distance,
    predict_constant_velocity_position,
)


class TestPolicePrediction(unittest.TestCase):
    """Test suite for constant-velocity position prediction and Euclidean distance."""

    def test_zero_elapsed_ticks(self) -> None:
        """Verify elapsed_ticks=0 returns the starting position unchanged."""
        pos = predict_constant_velocity_position(10.0, -5.0, 2.5, 3.0, 0)
        self.assertEqual(pos, Point2D(10.0, -5.0))
        self.assertEqual(pos.x, 10.0)
        self.assertEqual(pos.y, -5.0)

    def test_stationary_object(self) -> None:
        """Verify stationary objects (vx=0, vy=0) stay in place over multiple ticks."""
        pos = predict_constant_velocity_position(42.0, 100.0, 0.0, 0.0, 25.0)
        self.assertEqual(pos, Point2D(42.0, 100.0))

    def test_positive_and_negative_velocities(self) -> None:
        """Verify motion correctly updates coordinates for mixed-sign velocity vectors."""
        # Moving right (+x) and down (-y): x=10 + 3*4 = 22, y=20 + (-5)*4 = 0
        pos = predict_constant_velocity_position(10.0, 20.0, 3.0, -5.0, 4.0)
        self.assertEqual(pos, Point2D(22.0, 0.0))

        # Moving left (-x) and up (+y): x=-5 + (-2)*3 = -11, y=0 + 4*3 = 12
        pos2 = predict_constant_velocity_position(-5.0, 0.0, -2.0, 4.0, 3.0)
        self.assertEqual(pos2, Point2D(-11.0, 12.0))

    def test_multiple_elapsed_ticks(self) -> None:
        """Verify position scales linearly with elapsed ticks."""
        p0 = (0.0, 0.0)
        vx, vy = 1.5, -2.0
        for ticks in [1, 2, 5, 10, 50, 100]:
            predicted = predict_constant_velocity_position(p0[0], p0[1], vx, vy, ticks)
            self.assertAlmostEqual(predicted.x, vx * ticks)
            self.assertAlmostEqual(predicted.y, vy * ticks)

    def test_euclidean_distance_known_example(self) -> None:
        """Verify Euclidean distance on standard 3-4-5 and known triangles."""
        # 3-4-5 triangle: (0, 0) to (3, 4) -> 5.0
        d1 = calculate_euclidean_distance((0.0, 0.0), (3.0, 4.0))
        self.assertEqual(d1, 5.0)

        # Offset triangle: (10, 10) to (13, 14) -> 5.0
        d2 = calculate_euclidean_distance(Point2D(10.0, 10.0), Point2D(13.0, 14.0))
        self.assertEqual(d2, 5.0)

        # Diagonal distance: (1, 1) to (4, 5) -> 5.0
        d3 = calculate_euclidean_distance((1, 1), (4, 5))
        self.assertEqual(d3, 5.0)

    def test_euclidean_distance_identical_positions(self) -> None:
        """Verify distance between identical positions is 0.0."""
        self.assertEqual(calculate_euclidean_distance((15.5, -3.2), (15.5, -3.2)), 0.0)
        self.assertEqual(calculate_euclidean_distance(Point2D(0.0, 0.0), Point2D(0.0, 0.0)), 0.0)

    def test_negative_elapsed_time_rejected(self) -> None:
        """Verify negative elapsed ticks raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            predict_constant_velocity_position(0.0, 0.0, 1.0, 1.0, -1)
        self.assertIn("elapsed_ticks must be non-negative", str(ctx.exception))

    def test_booleans_and_strings_rejected(self) -> None:
        """Verify non-numeric types and booleans raise TypeError in both functions."""
        # Test predict_constant_velocity_position type errors
        bad_values = [True, False, "10", None, [1.0]]
        for val in bad_values:
            with self.subTest(bad_val=val):
                with self.assertRaises(TypeError):
                    predict_constant_velocity_position(val, 0.0, 1.0, 1.0, 5)  # type: ignore[arg-type]
                with self.assertRaises(TypeError):
                    predict_constant_velocity_position(0.0, 0.0, 1.0, 1.0, val)  # type: ignore[arg-type]

        # Test calculate_euclidean_distance type errors
        with self.assertRaises(TypeError):
            calculate_euclidean_distance((True, 0.0), (1.0, 1.0))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            calculate_euclidean_distance("origin", (1.0, 1.0))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            calculate_euclidean_distance((0.0, "bad"), (1.0, 1.0))  # type: ignore[arg-type]

    def test_nan_and_infinite_values_rejected(self) -> None:
        """Verify NaN, +inf, and -inf raise ValueError in both functions."""
        non_finites = [float("nan"), float("inf"), float("-inf")]

        # Prediction rejection
        for val in non_finites:
            with self.subTest(bad_prediction_val=val):
                with self.assertRaises(ValueError):
                    predict_constant_velocity_position(val, 0.0, 1.0, 1.0, 5)
                with self.assertRaises(ValueError):
                    predict_constant_velocity_position(0.0, val, 1.0, 1.0, 5)
                with self.assertRaises(ValueError):
                    predict_constant_velocity_position(0.0, 0.0, val, 1.0, 5)
                with self.assertRaises(ValueError):
                    predict_constant_velocity_position(0.0, 0.0, 1.0, val, 5)
                with self.assertRaises(ValueError):
                    predict_constant_velocity_position(0.0, 0.0, 1.0, 1.0, val)

        # Distance rejection
        for val in non_finites:
            with self.subTest(bad_distance_val=val):
                with self.assertRaises(ValueError):
                    calculate_euclidean_distance((val, 0.0), (1.0, 1.0))
                with self.assertRaises(ValueError):
                    calculate_euclidean_distance((0.0, 0.0), (1.0, val))

    def test_distance_wrong_length_rejected(self) -> None:
        """Verify points with != 2 coordinates raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_euclidean_distance((1.0,), (1.0, 2.0))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            calculate_euclidean_distance((1.0, 2.0, 3.0), (1.0, 2.0))  # type: ignore[arg-type]

    def test_large_valid_inputs_remain_finite(self) -> None:
        """Verify large valid inputs calculate accurately without overflow or corruption."""
        pos = predict_constant_velocity_position(1_000_000.0, -500_000.0, 100.0, -50.0, 300)
        self.assertEqual(pos, Point2D(1_030_000.0, -515_000.0))
        self.assertTrue(math.isfinite(pos.x))
        self.assertTrue(math.isfinite(pos.y))

        dist = calculate_euclidean_distance((0.0, 0.0), (3_000_000.0, 4_000_000.0))
        self.assertEqual(dist, 5_000_000.0)


if __name__ == "__main__":
    unittest.main()
