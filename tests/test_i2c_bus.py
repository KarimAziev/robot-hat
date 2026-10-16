import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

from robot_hat.i2c.i2c_bus import I2CBus


class TestI2CBus(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = MagicMock()
        patcher = patch("robot_hat.i2c.i2c_bus.SMBus", return_value=self.backend)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.bus = I2CBus(1)
        self.addCleanup(self.bus.close)

    def test_transactions_to_different_addresses_cannot_overlap(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        second_started = threading.Event()
        second_entered = threading.Event()
        selected_address = 0

        def read(address: int, register: int, force: bool | None = None) -> int:
            nonlocal selected_address
            selected_address = address
            if address == 0x5F:
                entered.set()
                if not release.wait(2):
                    raise AssertionError("test transaction was not released")
            else:
                second_entered.set()
            return selected_address

        def second_read() -> int:
            second_started.set()
            return self.bus.read_byte_data(0x40, 0x0F)

        self.backend.read_byte_data.side_effect = read
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(self.bus.read_byte_data, 0x5F, 0x0F)
            self.assertTrue(entered.wait(2))
            second = executor.submit(second_read)
            try:
                self.assertTrue(second_started.wait(2))
                self.assertFalse(second_entered.wait(0.05))
            finally:
                release.set()
            self.assertEqual(first.result(timeout=2), 0x5F)
            self.assertEqual(second.result(timeout=2), 0x40)

    def test_close_waits_for_active_transaction_and_rejects_further_io(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        close_started = threading.Event()
        closed = threading.Event()

        def read(*args: object) -> int:
            entered.set()
            if not release.wait(2):
                raise AssertionError("test transaction was not released")
            return 42

        def close() -> None:
            close_started.set()
            self.bus.close()
            closed.set()

        self.backend.read_byte.side_effect = read
        with ThreadPoolExecutor(max_workers=2) as executor:
            pending = executor.submit(self.bus.read_byte, 0x5F)
            self.assertTrue(entered.wait(2))
            closing = executor.submit(close)
            try:
                self.assertTrue(close_started.wait(2))
                self.assertFalse(closed.wait(0.05))
                self.backend.close.assert_not_called()
            finally:
                release.set()
            self.assertEqual(pending.result(timeout=2), 42)
            closing.result(timeout=2)
        self.backend.close.assert_called_once()
        with self.assertRaisesRegex(RuntimeError, "closed"):
            self.bus.read_byte(0x5F)

    def test_context_exit_notifies_close_listeners_once(self) -> None:
        listener = MagicMock()
        self.bus.emitter.on("close", listener)
        with self.bus:
            pass
        self.bus.close()
        listener.assert_called_once_with(self.bus)
        self.backend.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
