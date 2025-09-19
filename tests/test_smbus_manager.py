import threading
import unittest
from unittest.mock import patch

from robot_hat.common.event_emitter import EventEmitter
from robot_hat.exceptions import InvalidBusType
from robot_hat.i2c.smbus_manager import SMBusManager


class DummyI2CBus:
    """
    A small dummy replacement for I2CBus used for testing.
    Mimics the interface expected by SMBusManager.
    """

    def __init__(self, bus, force=False):
        self._bus = bus
        self.force = force
        self.emitter = EventEmitter()
        self.closed = False

    def close(self):
        """
        Simulate closing the bus by setting a flag and emitting the "close" event.
        """
        self.closed = True
        self.emitter.emit("close", self)

    def open(self, bus):
        pass


class TestSMBusManager(unittest.TestCase):
    def setUp(self):
        SMBusManager._instances.clear()

    def tearDown(self):
        SMBusManager.close_all()

    @patch("robot_hat.i2c.i2c_bus.I2CBus", new=DummyI2CBus)
    def test_get_bus_singleton_int(self):
        bus1 = SMBusManager.get_bus(0)
        bus2 = SMBusManager.get_bus(0)
        self.assertIs(bus1, bus2)
        self.assertEqual(bus1._bus, "/dev/i2c-0")

    @patch("robot_hat.i2c.i2c_bus.I2CBus", new=DummyI2CBus)
    def test_get_bus_singleton_str(self):
        bus_path = "/dev/i2c-0"
        bus1 = SMBusManager.get_bus(bus_path)
        bus2 = SMBusManager.get_bus(0)
        self.assertIs(bus1, bus2)
        self.assertEqual(bus1._bus, bus_path)

    @patch("robot_hat.i2c.i2c_bus.I2CBus", new=DummyI2CBus)
    def test_get_bus_invalid_type(self):
        with self.assertRaises(InvalidBusType):
            SMBusManager.get_bus(3.14)  # type: ignore

    @patch("robot_hat.i2c.i2c_bus.I2CBus", new=DummyI2CBus)
    def test_close_bus(self):
        bus = SMBusManager.get_bus(1)
        normalized = SMBusManager._normalize_bus(1)
        self.assertIn(normalized, SMBusManager._instances)

        SMBusManager.close_bus(1)
        self.assertNotIn(normalized, SMBusManager._instances)

        if hasattr(bus, "closed"):
            self.assertTrue(bus.closed)  # type: ignore

    @patch("robot_hat.i2c.i2c_bus.I2CBus", new=DummyI2CBus)
    def test_close_all(self):
        bus0 = SMBusManager.get_bus(0)
        bus1 = SMBusManager.get_bus(1)
        self.assertIn("/dev/i2c-0", SMBusManager._instances)
        self.assertIn("/dev/i2c-1", SMBusManager._instances)

        SMBusManager.close_all()
        self.assertEqual(len(SMBusManager._instances), 0)

        if hasattr(bus0, "closed"):
            self.assertTrue(bus0.closed)  # type: ignore
        if hasattr(bus1, "closed"):
            self.assertTrue(bus1.closed)  # type: ignore

    @patch("robot_hat.i2c.i2c_bus.I2CBus", new=DummyI2CBus)
    def test_on_bus_close_removes_instance(self):
        bus = SMBusManager.get_bus(2)
        normalized = SMBusManager._normalize_bus(2)
        self.assertIn(normalized, SMBusManager._instances)
        bus.close()
        self.assertNotIn(normalized, SMBusManager._instances)

    @patch("robot_hat.i2c.i2c_bus.I2CBus", new=DummyI2CBus)
    def test_thread_safety_of_get_bus(self):
        bus_instances = []
        exception_list = []

        def get_bus():
            try:
                bus = SMBusManager.get_bus(3)
                bus_instances.append(bus)
            except Exception as exc:
                exception_list.append(exc)

        threads = [threading.Thread(target=get_bus) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(exception_list), 0)
        self.assertTrue(all(bus is bus_instances[0] for bus in bus_instances))


if __name__ == "__main__":
    unittest.main()
