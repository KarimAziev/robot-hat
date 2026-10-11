import unittest
from abc import ABC, abstractmethod
from typing import Callable
from unittest.mock import Mock, patch

from robot_hat.i2c.retry_decorator import (
    INITIAL_WAIT,
    JITTER,
    MAX_WAIT,
    RETRY_ATTEMPTS,
    RETRY_DECORATOR,
)


class _ReaderABC(ABC):
    @abstractmethod
    def read(self, register: int, /, *, offset: int = 0) -> int:
        pass


class _Reader(_ReaderABC):
    @RETRY_DECORATOR
    def read(self, register: int, /, *, offset: int = 0) -> int:
        """Read a register with an optional offset."""
        return register + offset


class TestRetryDecorator(unittest.TestCase):
    def test_method_binding_and_signature(self) -> None:
        reader = _Reader()
        read: Callable[[int], int] = reader.read

        self.assertEqual(read(10), 10)
        self.assertEqual(reader.read(10, offset=2), 12)
        self.assertEqual(_Reader.read(reader, 10, offset=3), 13)
        self.assertEqual(reader.read.__name__, "read")
        self.assertEqual(
            reader.read.__doc__, "Read a register with an optional offset."
        )

    def test_transient_errors_are_retried(self) -> None:
        operation = Mock(side_effect=[OSError("busy"), TimeoutError("timeout"), 42])

        @RETRY_DECORATOR
        def read(register: int, /, *, offset: int = 0) -> int:
            return operation(register, offset=offset)

        with patch("tenacity.nap.time.sleep") as sleep:
            result: int = read(10, offset=2)

        self.assertEqual(result, 42)
        self.assertEqual(operation.call_count, 3)
        operation.assert_called_with(10, offset=2)
        self.assertEqual(sleep.call_count, 2)

    def test_exhausted_retries_reraise_original_error(self) -> None:
        error = OSError("bus unavailable")
        operation = Mock(side_effect=error)

        @RETRY_DECORATOR
        def read() -> int:
            return operation()

        with patch("tenacity.nap.time.sleep") as sleep:
            with self.assertRaises(OSError) as caught:
                read()

        self.assertIs(caught.exception, error)
        self.assertEqual(operation.call_count, RETRY_ATTEMPTS)
        self.assertEqual(sleep.call_count, RETRY_ATTEMPTS - 1)

    def test_other_errors_are_not_retried(self) -> None:
        error = ValueError("invalid register")
        operation = Mock(side_effect=error)

        @RETRY_DECORATOR
        def read() -> int:
            return operation()

        with patch("tenacity.nap.time.sleep") as sleep:
            with self.assertRaises(ValueError) as caught:
                read()

        self.assertIs(caught.exception, error)
        operation.assert_called_once_with()
        sleep.assert_not_called()

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
