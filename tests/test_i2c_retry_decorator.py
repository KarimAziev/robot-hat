import unittest

from robot_hat.i2c.retry_decorator import (
    INITIAL_WAIT,
    JITTER,
    MAX_WAIT,
    RETRY_ATTEMPTS,
    RETRY_DECORATOR,
)


class TestRetryDecorator(unittest.TestCase):
    def test_constants_values(self):
        """Test that the retry decorator constants have expected values."""
        self.assertEqual(RETRY_ATTEMPTS, 5)
        self.assertEqual(INITIAL_WAIT, 0.01)
        self.assertEqual(MAX_WAIT, 0.2)
        self.assertEqual(JITTER, 0.05)

    def test_retry_decorator_exists(self):
        """Test that RETRY_DECORATOR is defined."""
        self.assertIsNotNone(RETRY_DECORATOR)

    def test_retry_decorator_type(self):
        """Test that RETRY_DECORATOR is a retry decorator."""
        self.assertTrue(callable(RETRY_DECORATOR))

    def test_retry_decorator_attributes(self):
        """Test that RETRY_DECORATOR has expected attributes."""
        self.assertTrue(hasattr(RETRY_DECORATOR, "__name__"))

    def test_constants_types(self):
        """Test that constants have correct types."""
        self.assertIsInstance(RETRY_ATTEMPTS, int)
        self.assertIsInstance(INITIAL_WAIT, float)
        self.assertIsInstance(MAX_WAIT, float)
        self.assertIsInstance(JITTER, float)

    def test_constants_positive_values(self):
        """Test that all constants have positive values."""
        self.assertGreater(RETRY_ATTEMPTS, 0)
        self.assertGreater(INITIAL_WAIT, 0)
        self.assertGreater(MAX_WAIT, 0)
        self.assertGreater(JITTER, 0)

    def test_wait_time_relationship(self):
        """Test that wait time relationships are logical."""
        self.assertLess(INITIAL_WAIT, MAX_WAIT)
        self.assertLess(JITTER, MAX_WAIT)

    def test_retry_attempts_reasonable(self):
        """Test that retry attempts is a reasonable number."""
        self.assertGreaterEqual(RETRY_ATTEMPTS, 3)
        self.assertLessEqual(RETRY_ATTEMPTS, 10)

    def test_wait_times_reasonable(self):
        """Test that wait times are reasonable for I2C operations."""
        self.assertLessEqual(INITIAL_WAIT, 0.1)

        self.assertLessEqual(MAX_WAIT, 1.0)

        self.assertLess(JITTER, MAX_WAIT)


if __name__ == "__main__":
    unittest.main()
