import errno
import logging
import os
from types import TracebackType
from typing import TYPE_CHECKING, Callable, List, Optional, Sequence, Type, Union

from robot_hat.interfaces.smbus_abc import SMBusABC
import sys

if TYPE_CHECKING:
    from smbus2 import i2c_msg

logger = logging.getLogger(__name__)

I2C_ALLOWED_ADDRESES = [20, 54]


def generate_discharge_sequence(
    start_voltage: float,
    end_voltage: float,
    *,
    amount: Optional[int] = None,
    rate: Optional[int] = None,
    conversion_fn: Optional[Callable[[float], int]] = None,
) -> List[int]:
    """
    Generate a flattened list of raw values (split into MSB and LSB)
    simulating a discharge over a specified voltage range.

    Args:
      start_voltage (float): The starting voltage (e.g. full voltage).
      end_voltage (float): The ending voltage (e.g. empty voltage).
      amount (int, optional): Number of discharge points (evenly spaced).
      rate (int, optional): The decrement for raw value if amount not provided.
      conversion_fn (Callable[[float], int], optional):
          A function that converts a voltage (in Volts) to a raw integer value.
          If not provided, a default ADC conversion is used:
            raw = int((voltage * 4095) / 3.3)

    Returns:
      List[int]: A flat list of bytes [MSB, LSB, MSB, LSB, …] representing
                 successive raw readings.
    """
    if start_voltage < end_voltage:
        raise ValueError(
            "Start voltage must be greater than or equal to the end voltage."
        )
    if amount is not None and rate is not None:
        raise ValueError("Specify either 'amount' or 'rate', but not both.")

    if conversion_fn is None:

        def conversion_fn_default(voltage: float) -> int:
            return int((voltage * 4095) / 3.3)

        conversion_fn = conversion_fn_default

    start_raw_value = conversion_fn(start_voltage)
    end_raw_value = conversion_fn(end_voltage)

    if amount is not None:
        discharge_values = [
            int(
                start_raw_value - i * ((start_raw_value - end_raw_value) / (amount - 1))
            )
            for i in range(amount)
        ]
    elif rate is not None:
        discharge_values = list(range(start_raw_value, end_raw_value - 1, -rate))
    else:
        discharge_values = list(range(start_raw_value, end_raw_value - 1, -1))

    discharge_sequence = []
    for raw_value in discharge_values:
        msb = raw_value >> 8
        lsb = raw_value & 0xFF
        discharge_sequence.extend([msb, lsb])
    return discharge_sequence


def ina219_bus_voltage_conversion(bus_voltage: float) -> int:
    """
    Convert a desired bus voltage into the raw value expected by the INA219.

    The INA219 returns a 16-bit value. When reading, the driver shifts it right by 3
    and multiplies by 0.004 to recover the voltage:
      bus_voltage = (raw >> 3) * 0.004
    Therefore, to simulate a given bus voltage you must generate a raw value as:
      raw_after_shift = bus_voltage / 0.004
      raw_value = raw_after_shift << 3
    """
    return int(bus_voltage / 0.004) << 3


def ina219_shunt_voltage_conversion(shunt_voltage: float) -> int:
    """Convert a shunt voltage (volts) into the INA219 shunt register value."""

    return int(shunt_voltage / 0.00001)


def ina219_current_conversion(current_a: float, current_lsb_ma: float = 0.1) -> int:
    """Convert a current (amps) into the INA219 current register value."""

    current_ma = current_a * 1000.0
    if current_lsb_ma <= 0:
        current_lsb_ma = 0.1
    return int(current_ma / current_lsb_ma)


def ina219_power_conversion(power_w: float, power_lsb_w: float = 0.002) -> int:
    """Convert a power reading (watts) into the INA219 power register value."""

    if power_lsb_w <= 0:
        power_lsb_w = 0.002
    return int(power_w / power_lsb_w)


class MockSMBus(SMBusABC):
    def __init__(self, bus: Union[None, int, str], force: bool = False) -> None:
        self.bus = bus
        self.force = force
        self.fd = None
        self.pec = 0
        self.address = None
        self._force_last = None

        self._discharge_sequences = {}
        self._discharge_profile = None

        self._command_responses = {
            "byte": 0x10,
            "word": 0x1234,
            "block": [12, 154, 3, 4, 5],
        }

        self._command_responses_by_addr = {"3": []}

        self._byte_responses_by_addrs = {
            "20": [],
        }

    def open(self, bus: Union[int, str]) -> None:
        self.fd = 1
        self.bus = bus

    def close(self) -> None:
        self.fd = None

    def write_quick(self, i2c_addr: int, force: Optional[bool] = None) -> None:
        self._set_address(i2c_addr, force)
        return

    def read_byte(self, i2c_addr: int, force: Optional[bool] = None) -> int:
        logger.debug("read_byte: %s", i2c_addr)
        self._set_address(i2c_addr, force)
        byte_responses = self._byte_responses_by_addrs.get(f"{i2c_addr}")
        if byte_responses is None:
            return self._command_responses["byte"]
        if len(byte_responses) == 0:
            DISCHARGE_RATE = os.getenv("ROBOT_HAT_DISCHARGE_RATE")
            START_VOLTAGE_MOCK = os.getenv("ROBOT_HAT_START_VOLTAGE_MOCK")
            END_VOLTAGE_MOCK = os.getenv("ROBOT_HAT_END_VOLTAGE_MOCK")
            rate = int(DISCHARGE_RATE) if DISCHARGE_RATE is not None else 20
            start_voltage = (
                float(START_VOLTAGE_MOCK) if START_VOLTAGE_MOCK is not None else 2.6
            )
            end_voltage = (
                float(END_VOLTAGE_MOCK) if END_VOLTAGE_MOCK is not None else 2.0
            )

            self._byte_responses_by_addrs[f"{i2c_addr}"] = generate_discharge_sequence(
                start_voltage=start_voltage, end_voltage=end_voltage, rate=rate
            )
            byte_responses = self._byte_responses_by_addrs[f"{i2c_addr}"]
        return byte_responses.pop(0)

    def write_byte(
        self, i2c_addr: int, value: int, force: Optional[bool] = None
    ) -> None:
        logger.debug("write_byte: %s", value)
        if i2c_addr not in I2C_ALLOWED_ADDRESES:
            raise OSError(
                errno.EREMOTEIO
                if sys.platform != "win32" and sys.platform != "darwin"
                else errno.ENXIO,
                "No such device or address",
            )
        self._set_address(i2c_addr, force)
        return

    def read_byte_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> int:
        logger.debug("read_byte_data: %s", register)
        self._set_address(i2c_addr, force)
        return self._command_responses["byte"]

    def write_byte_data(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> None:
        logger.debug("write_byte_data '%s' to '%s'", register, value)
        self._set_address(i2c_addr, force)
        return

    def read_word_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> int:
        logger.debug("read_word_data from register '%s'", register)
        self._set_address(i2c_addr, force)
        return self._command_responses["word"]

    def write_word_data(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> None:
        logger.debug("write_word_data %s to register '%s'", value, register)
        self._set_address(i2c_addr, force)
        return

    def process_call(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> int:
        logger.debug("write_word_data %s to register '%s'", value, register)
        self._set_address(i2c_addr, force)
        return self._command_responses["word"]

    def read_block_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> List[int]:
        logger.debug("read_block_data register '%s'", register)
        self._set_address(i2c_addr, force)
        return self._command_responses["block"]

    def write_block_data(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ) -> None:
        logger.debug("write_block_data %s to register '%s'", data, register)
        self._set_address(i2c_addr, force)
        return

    def block_process_call(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ) -> List[int]:
        logger.debug("block_process_call %s to register '%s'", data, register)
        self._set_address(i2c_addr, force)
        return self._command_responses["block"]

    def write_i2c_block_data(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ) -> None:
        logger.debug("write_i2c_block_data %s to register %s", data, register)
        self._set_address(i2c_addr, force)
        return

    def _load_discharge_profile(self) -> dict:
        if self._discharge_profile is None:
            amount_env = os.getenv("ROBOT_HAT_DISCHARGE_POINTS")
            rate_env = os.getenv("ROBOT_HAT_DISCHARGE_RATE")

            amount = int(amount_env) if amount_env is not None else None
            if amount is not None and amount < 2:
                amount = 2

            rate = int(rate_env) if rate_env is not None else None
            if amount is None and rate is None:
                rate = 10

            start_voltage = float(os.getenv("ROBOT_HAT_START_VOLTAGE_MOCK", "12.6"))
            end_voltage = float(os.getenv("ROBOT_HAT_END_VOLTAGE_MOCK", "8.0"))
            start_current = float(os.getenv("ROBOT_HAT_START_CURRENT_MOCK", "5.0"))
            end_current = float(os.getenv("ROBOT_HAT_END_CURRENT_MOCK", "0.5"))
            shunt_resistance = float(
                os.getenv("ROBOT_HAT_SHUNT_RESISTANCE_MOCK", "0.01")
            )
            current_lsb_ma = float(os.getenv("ROBOT_HAT_CURRENT_LSB_MOCK_MA", "0.1"))
            power_lsb_w = float(os.getenv("ROBOT_HAT_POWER_LSB_MOCK_W", "0.002"))

            if start_voltage < end_voltage:
                start_voltage, end_voltage = end_voltage, start_voltage
            if start_current < end_current:
                start_current, end_current = end_current, start_current

            self._discharge_profile = {
                "amount": amount,
                "rate": rate,
                "start_voltage": start_voltage,
                "end_voltage": end_voltage,
                "start_current": start_current,
                "end_current": end_current,
                "shunt_resistance": shunt_resistance,
                "current_lsb_ma": current_lsb_ma,
                "power_lsb_w": power_lsb_w,
            }

        return self._discharge_profile

    def _ensure_discharge_sequence(self, register: int) -> List[int]:
        profile = self._load_discharge_profile()

        sequence = self._discharge_sequences.get(register)
        if sequence:
            return sequence

        generator_kwargs = {}
        if profile["amount"] is not None:
            generator_kwargs["amount"] = profile["amount"]
        else:
            generator_kwargs["rate"] = profile["rate"]

        if register == 1:
            start = profile["start_current"] * profile["shunt_resistance"]
            end = profile["end_current"] * profile["shunt_resistance"]
            conversion_fn = ina219_shunt_voltage_conversion
        elif register == 2:
            start = profile["start_voltage"]
            end = profile["end_voltage"]
            conversion_fn = ina219_bus_voltage_conversion
        elif register == 3:
            start = profile["start_voltage"] * profile["start_current"]
            end = profile["end_voltage"] * profile["end_current"]
            conversion_fn = lambda power: ina219_power_conversion(
                power, profile["power_lsb_w"]
            )
        elif register == 4:
            start = profile["start_current"]
            end = profile["end_current"]
            conversion_fn = lambda current: ina219_current_conversion(
                current, profile["current_lsb_ma"]
            )
        else:
            start = profile["start_voltage"]
            end = profile["end_voltage"]
            conversion_fn = ina219_bus_voltage_conversion

        if start < end:
            start, end = end, start

        sequence = generate_discharge_sequence(
            start,
            end,
            conversion_fn=conversion_fn,
            **generator_kwargs,
        )
        self._discharge_sequences[register] = sequence
        return sequence

    def read_i2c_block_data(
        self, i2c_addr: int, register: int, length: int, force: Optional[bool] = None
    ) -> List[int]:
        logger.debug("read_i2c_block_data register: %s", register)
        self._set_address(i2c_addr, force)

        if register in (1, 2, 3, 4):
            sequence = self._ensure_discharge_sequence(register)
            if len(sequence) < length:
                data = sequence if sequence else [0] * length
                self._discharge_sequences[register] = []
            else:
                data = sequence[:length]
                self._discharge_sequences[register] = sequence[length:]
            logger.debug(
                "Simulated discharge response for register %s: %s", register, data
            )
            return data
        else:
            return self._command_responses["block"][:length]

    def i2c_rdwr(self, *i2c_msgs: "i2c_msg") -> None:
        logger.debug("%s", i2c_msgs)
        return

    def enable_pec(self, enable=True) -> None:
        self.pec = int(enable)

    def __enter__(self) -> "MockSMBus":
        """Enter handler."""
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Exit handler."""
        self.close()

    def _set_address(self, address: int, force: Optional[bool] = None) -> None:
        """
        Set i2c slave address to use for subsequent calls.

        :param address:
        :type address: int
        :param force:
        :type force: Boolean
        """
        force = force if force is not None else self.force
        if self.address != address or self._force_last != force:
            if force is True:
                logger.debug("ioctl(self.fd, I2C_SLAVE_FORCE, address)")
            else:
                logger.debug("ioctl(self.fd, I2C_SLAVE, address)")
            self.address = address
            self._force_last = force

    def _get_funcs(self) -> int:
        """
        Returns a 32-bit value stating supported I2C functions.

        :rtype: int
        """

        return 0x03660001


if __name__ == "__main__":
    mock_bus = MockSMBus(1)
    mock_bus.open(1)

    print("Read byte:", mock_bus.read_byte(0x10))
    print("Read word:", mock_bus.read_word_data(0x10, 0x01))
    print("Read block:", mock_bus.read_block_data(0x10, 0x01))

    mock_bus.close()

    mock_bus = MockSMBus(1)
    mock_bus.open(1)

    count = len(mock_bus._byte_responses_by_addrs["20"]) + 1

    for i in range(count):
        res = mock_bus.read_byte(20)
        print(f"{i}: {res}, len: {len(mock_bus._byte_responses_by_addrs['20'])}")

    mock_bus.close()
