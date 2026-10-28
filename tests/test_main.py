"""Unit tests for the main entry point."""

import io
import unittest
from unittest.mock import patch

import main


class TestMainEntryPoint(unittest.TestCase):
    """Test suite for main.py entry point execution."""

    def test_main_exits_cleanly(self) -> None:
        """Verify main() emits standby status to stderr and exits with 0."""
        stderr_capture = io.StringIO()
        with patch("sys.stderr", stderr_capture), self.assertRaises(SystemExit) as ctx:
            main.main()
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("Subway Escape Bot", stderr_capture.getvalue())
        self.assertIn("Awaiting official hackathon starter template", stderr_capture.getvalue())


if __name__ == "__main__":
    unittest.main()
