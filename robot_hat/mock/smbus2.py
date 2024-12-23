import errno
import logging
import os
from typing import List, Optional, Sequence, Union

from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
    from smbus2 import i2c_msg

logger = logging.getLogger(__name__)

I2C_ALLOWED_ADDRESES = [20, 54]


def generate_discharge_sequence(
    start_voltage=2.6, end_voltage=2.0, amount: Optional[int] = None, rate=20
):
    """
    Generate a flattened list of MSB and LSB values simulating a discharge
    over a specified range of voltages, with control over the number of points or step size.

    Args:
        start_voltage (float): The starting voltage (e.g., 2.6 for ~2.6 V).
        end_voltage (float): The ending voltage (e.g., 2.0 for ~2.0 V).
        amount (int, optional): The number of discharge points (equally spaced).
        rate (int, optional): Step size for raw value decrement (e.g., 20 for faster discharge).

    Returns:
        List[int]: A flattened list containing MSB and LSB values in decreasing order.
                   For example, [12, 159, 12, 158, ..., 9, 178].
    """

    if start_voltage < end_voltage:
        raise ValueError(
            "Start voltage must be greater than or equal to the end voltage."
        )
    if amount is not None and rate is not None:
        raise ValueError("Specify either 'amount' or 'rate', but not both.")

    def voltage_to_raw(voltage):
        return int((voltage * 4095) / 3.3)

    start_raw_value = voltage_to_raw(start_voltage)
    end_raw_value = voltage_to_raw(end_voltage)

    if amount is not None:
        discharge_values = [
            int(
                start_raw_value - i * ((start_raw_value - end_raw_value) / (amount - 1))
            )
            for i in range(amount)
        ]
    elif rate is not None:
        discharge_values = range(start_raw_value, end_raw_value - 1, -rate)
    else:
        discharge_values = range(start_raw_value, end_raw_value - 1, -1)

    discharge_sequence = []
    for raw_value in discharge_values:
        msb = raw_value >> 8  # Extract MSB
        lsb = raw_value & 0xFF  # Extract LSB
        discharge_sequence.extend([msb, lsb])

    return discharge_sequence


class MockSMBus:
    def __init__(self, bus: Union[None, int, str], force: bool = False):
        self.bus = bus
        self.force = force
        self.fd = None
        self.pec = 0
        self.address = None
        self._force_last = None

        self._command_responses = {
            "byte": 0x10,
            "word": 0x1234,
            "block": [1, 2, 3, 4, 5],
        }

        self._byte_responses_by_addrs = {
            "20": [],
        }

    def open(self, bus: Union[int, str]) -> None:
        self.fd = 1
        self.bus = bus

    def close(self) -> None:
        self.fd = None

    def _set_address(self, address: int, force: Optional[bool] = None):
        self.address = address
        self._force_last = force or self.force

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
            rate = int(DISCHARGE_RATE) if DISCHARGE_RATE is not None else 20

            self._byte_responses_by_addrs[f"{i2c_addr}"] = generate_discharge_sequence(
                rate=rate
            )
            byte_responses = self._byte_responses_by_addrs[f"{i2c_addr}"]
        return byte_responses.pop(0)

    def write_byte(
        self, i2c_addr: int, value: int, force: Optional[bool] = None
    ) -> None:
        logger.debug("write_byte: %s", value)
        if i2c_addr not in I2C_ALLOWED_ADDRESES:
            raise OSError(errno.EREMOTEIO, "No such device or address")
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
    ):
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
    ):
        logger.debug("block_process_call %s to register '%s'", data, register)
        self._set_address(i2c_addr, force)
        return self._command_responses["block"]

    def write_i2c_block_data(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ):
        logger.debug("write_i2c_block_data %s to register '%s'", data, register)
        self._set_address(i2c_addr, force)
        return

    def read_i2c_block_data(
        self, i2c_addr: int, register: int, length: int, force: Optional[bool] = None
    ) -> List[int]:
        logger.debug("read_i2c_block_data register: %s", register)
        self._set_address(i2c_addr, force)
        return self._command_responses["block"][:length]

    def i2c_rdwr(self, *i2c_msgs: "i2c_msg") -> None:
        logger.debug("%s", i2c_msgs)
        return

    def enable_pec(self, enable=True) -> None:
        self.pec = int(enable)  # Simulate enabling PEC


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
