"""Unit tests for the exponential money decay module."""

import math
import unittest

from src.strategy.money import calculate_exponential_decay


class TestMoneyDecay(unittest.TestCase):
    """Test suite for calculate_exponential_decay function."""

    def test_zero_elapsed_time(self) -> None:
        """Verify elapsed_time=0 returns initial_value exactly with no decay."""
        self.assertEqual(calculate_exponential_decay(100.0, 0.05, 0.0), 100.0)
        self.assertEqual(calculate_exponential_decay(50, 0.2, 0), 50.0)
        self.assertEqual(calculate_exponential_decay(0.0, 0.1, 0.0), 0.0)

    def test_zero_decay_rate(self) -> None:
        """Verify decay_rate=0 preserves initial_value regardless of elapsed time."""
        self.assertEqual(calculate_exponential_decay(250.0, 0.0, 10.0), 250.0)
        self.assertEqual(calculate_exponential_decay(500, 0, 300), 500.0)

    def test_known_numerical_example(self) -> None:
        """Verify result matches theoretical value M(t) = M0 * exp(-lambda * t)."""
        # M0 = 100.0, lambda = 0.05, t = 10.0 => 100 * exp(-0.5) ~= 60.653065971263345
        m0 = 100.0
        lam = 0.05
        t = 10.0
        expected = m0 * math.exp(-lam * t)
        actual = calculate_exponential_decay(m0, lam, t)
        self.assertAlmostEqual(actual, expected, places=9)
        self.assertAlmostEqual(actual, 60.653065971, places=6)

        # Another example: half-life check where lambda * t = ln(2)
        half_life_t = math.log(2) / 0.1
        self.assertAlmostEqual(calculate_exponential_decay(200.0, 0.1, half_life_t), 100.0, places=9)

    def test_increasing_elapsed_time_monotonicity(self) -> None:
        """Verify that as elapsed time increases, remaining money monotonically decreases or stays equal."""
        m0 = 1000.0
        decay = 0.02
        times = [0.0, 1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 200.0, 300.0]
        values = [calculate_exponential_decay(m0, decay, t) for t in times]

        for i in range(len(values) - 1):
            self.assertGreaterEqual(
                values[i],
                values[i + 1],
                f"Monotonicity violated: M({times[i]})={values[i]} < M({times[i+1]})={values[i+1]}",
            )

    def test_larger_decay_rate_monotonicity(self) -> None:
        """Verify that as decay rate increases, remaining money monotonically decreases or stays equal."""
        m0 = 500.0
        t = 15.0
        rates = [0.0, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0]
        values = [calculate_exponential_decay(m0, r, t) for r in rates]

        for i in range(len(values) - 1):
            self.assertGreaterEqual(
                values[i],
                values[i + 1],
                f"Monotonicity violated: rate {rates[i]} yielded {values[i]} < rate {rates[i+1]} ({values[i+1]})",
            )

    def test_very_large_elapsed_times_no_crash(self) -> None:
        """Verify extreme time horizons underflow smoothly without overflow or crash."""
        # For t=1000 (exponent -50), result is a tiny subnormal/normal float close to 0
        val_1k = calculate_exponential_decay(1000.0, 0.05, 1_000.0)
        self.assertGreater(val_1k, 0.0)
        self.assertLess(val_1k, 1e-18)

        # For t=100,000 and above (exponent <= -5000), result underflows cleanly to 0.0
        self.assertEqual(calculate_exponential_decay(1000.0, 0.05, 100_000.0), 0.0)
        self.assertEqual(calculate_exponential_decay(1000.0, 0.05, 1_000_000.0), 0.0)
        self.assertEqual(calculate_exponential_decay(1000.0, 0.05, 1e9), 0.0)
        self.assertEqual(calculate_exponential_decay(1000.0, 0.05, 1e15), 0.0)

    def test_negative_inputs_rejected(self) -> None:
        """Verify negative initial_value, decay_rate, and elapsed_time raise ValueError."""
        # Negative initial value
        with self.assertRaises(ValueError) as ctx:
            calculate_exponential_decay(-10.0, 0.05, 5.0)
        self.assertIn("initial_value must be non-negative", str(ctx.exception))

        # Negative decay rate
        with self.assertRaises(ValueError) as ctx:
            calculate_exponential_decay(100.0, -0.01, 5.0)
        self.assertIn("decay_rate must be non-negative", str(ctx.exception))

        # Negative elapsed time
        with self.assertRaises(ValueError) as ctx:
            calculate_exponential_decay(100.0, 0.05, -2.0)
        self.assertIn("elapsed_time must be non-negative", str(ctx.exception))

    def test_nan_and_infinite_inputs_rejected(self) -> None:
        """Verify NaN, +inf, and -inf raise ValueError for all three parameters."""
        non_finite_values = [float("nan"), float("inf"), float("-inf")]

        for bad in non_finite_values:
            with self.subTest(param="initial_value", val=bad):
                with self.assertRaises(ValueError):
                    calculate_exponential_decay(bad, 0.05, 5.0)

            with self.subTest(param="decay_rate", val=bad):
                with self.assertRaises(ValueError):
                    calculate_exponential_decay(100.0, bad, 5.0)

            with self.subTest(param="elapsed_time", val=bad):
                with self.assertRaises(ValueError):
                    calculate_exponential_decay(100.0, 0.05, bad)

    def test_zero_initial_value(self) -> None:
        """Verify initial_value=0 always returns 0.0 regardless of parameters."""
        self.assertEqual(calculate_exponential_decay(0, 0.1, 10), 0.0)
        self.assertEqual(calculate_exponential_decay(0.0, 0.0, 0.0), 0.0)

    def test_type_validation_rejected(self) -> None:
        """Verify non-numeric types and booleans raise TypeError."""
        with self.assertRaises(TypeError):
            calculate_exponential_decay("100", 0.05, 5.0)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            calculate_exponential_decay(100.0, "fast", 5.0)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            calculate_exponential_decay(100.0, 0.05, [5.0])  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            calculate_exponential_decay(True, 0.05, 5.0)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
