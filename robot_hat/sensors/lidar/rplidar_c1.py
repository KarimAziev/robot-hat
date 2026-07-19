import logging
import time
from dataclasses import dataclass
from typing import Iterator, Optional

from robot_hat.data_types.config.lidar import RPLidarC1Config
from robot_hat.data_types.lidar import (
    LidarDeviceInfo,
    LidarHealth,
    LidarHealthStatus,
    LidarMeasurement,
)
from robot_hat.exceptions import (
    LidarConnectionError,
    LidarProtocolError,
    LidarStateError,
    LidarTimeoutError,
)
from robot_hat.interfaces.lidar_2d_abc import Lidar2DABC
from robot_hat.interfaces.uart_abc import UARTABC
from robot_hat.uart.serial_uart import SerialUART


_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ResponseDescriptor:
    payload_size: int
    send_mode: int
    data_type: int


class RPLidarC1(Lidar2DABC):
    """RPLIDAR C1 driver using Slamtec's Standard scan mode.

    The protocol implementation is intentionally separated from ``UARTABC``.
    A native Raspberry Pi UART, a USB-to-UART adapter, or ``MockUART`` can all
    carry the same 8N1 byte stream.
    """

    _SYNC_BYTE = 0xA5
    _ANSWER_SYNC = b"\xa5\x5a"
    _DESCRIPTOR_SIZE = 7
    _DESCRIPTOR_SIZE_MASK = 0x3FFFFFFF
    _DESCRIPTOR_SEND_MODE_SHIFT = 30
    _SEND_MODE_SINGLE = 0
    _SEND_MODE_MULTIPLE = 1

    _CMD_STOP = 0x25
    _CMD_SCAN = 0x20
    _CMD_RESET = 0x40
    _CMD_GET_DEVICE_INFO = 0x50
    _CMD_GET_DEVICE_HEALTH = 0x52

    _ANS_TYPE_DEVICE_INFO = 0x04
    _ANS_TYPE_DEVICE_HEALTH = 0x06
    _ANS_TYPE_MEASUREMENT = 0x81

    _DEVICE_INFO_SIZE = 20
    _DEVICE_HEALTH_SIZE = 3
    _MEASUREMENT_SIZE = 5

    def __init__(
        self,
        config: Optional[RPLidarC1Config] = None,
        *,
        uart: Optional[UARTABC] = None,
    ) -> None:
        self.config = config or RPLidarC1Config()
        self._owns_uart = uart is None
        self._uart = uart or SerialUART(self.config.uart_config)
        self._scanning = False

    @property
    def uart(self) -> UARTABC:
        return self._uart

    @property
    def is_connected(self) -> bool:
        return self._uart.is_open

    @property
    def is_scanning(self) -> bool:
        return self._scanning

    def connect(self) -> None:
        if self.is_connected:
            return
        self._uart.open()
        self._uart.reset_input_buffer()
        _log.debug("Connected RPLIDAR C1 on %s", self._uart.config.port)

    def disconnect(self) -> None:
        if not self.is_connected:
            return
        try:
            if self.is_scanning:
                self.stop_scan()
        finally:
            if self._owns_uart:
                self._uart.close()
        _log.debug("Disconnected RPLIDAR C1 on %s", self._uart.config.port)

    def _require_connected(self) -> None:
        if not self.is_connected:
            raise LidarConnectionError("RPLIDAR C1 is not connected")

    def _require_idle(self) -> None:
        self._require_connected()
        if self.is_scanning:
            raise LidarStateError("Operation is unavailable while a scan is active")

    def _write_all(self, data: bytes) -> None:
        written = self._uart.write(data)
        if written != len(data):
            raise LidarProtocolError(
                f"UART accepted {written} of {len(data)} command bytes"
            )

    def _send_command(self, command: int) -> None:
        self._write_all(bytes((self._SYNC_BYTE, command)))

    def _read_exact(self, size: int, context: str) -> bytes:
        result = bytearray()
        while len(result) < size:
            chunk = self._uart.read(size - len(result))
            if not chunk:
                raise LidarTimeoutError(
                    f"Timed out reading {context}: received {len(result)} of "
                    f"{size} bytes"
                )
            result.extend(chunk)
        return bytes(result)

    def _read_descriptor(self) -> _ResponseDescriptor:
        sync = bytearray()
        discarded = 0
        while bytes(sync) != self._ANSWER_SYNC:
            byte = self._read_exact(1, "response descriptor sync")
            sync.append(byte[0])
            if len(sync) > len(self._ANSWER_SYNC):
                del sync[0]
                discarded += 1
            if discarded > self.config.max_resync_bytes:
                raise LidarProtocolError("Unable to synchronize response descriptor")

        remainder = self._read_exact(
            self._DESCRIPTOR_SIZE - len(self._ANSWER_SYNC),
            "response descriptor",
        )
        size_and_mode = int.from_bytes(remainder[:4], "little")
        return _ResponseDescriptor(
            payload_size=size_and_mode & self._DESCRIPTOR_SIZE_MASK,
            send_mode=size_and_mode >> self._DESCRIPTOR_SEND_MODE_SHIFT,
            data_type=remainder[4],
        )

    def _request(
        self,
        command: int,
        *,
        expected_type: int,
        expected_size: int,
    ) -> bytes:
        self._require_idle()
        self._uart.reset_input_buffer()
        self._send_command(command)
        descriptor = self._read_descriptor()
        if descriptor.send_mode != self._SEND_MODE_SINGLE:
            raise LidarProtocolError(
                f"Expected a single response, got send mode {descriptor.send_mode}"
            )
        if descriptor.data_type != expected_type:
            raise LidarProtocolError(
                f"Expected response type 0x{expected_type:02X}, got "
                f"0x{descriptor.data_type:02X}"
            )
        if descriptor.payload_size != expected_size:
            raise LidarProtocolError(
                f"Expected {expected_size} response bytes, got "
                f"{descriptor.payload_size}"
            )
        return self._read_exact(expected_size, "response payload")

    @staticmethod
    def _model_name(model_id: int) -> str:
        major = model_id >> 4
        minor = model_id & 0x0F
        if major >= 4:
            return f"C{major - 3}M{minor}"
        return f"RPLIDAR-0x{model_id:02X}"

    def get_device_info(self) -> LidarDeviceInfo:
        payload = self._request(
            self._CMD_GET_DEVICE_INFO,
            expected_type=self._ANS_TYPE_DEVICE_INFO,
            expected_size=self._DEVICE_INFO_SIZE,
        )
        model_id = payload[0]
        firmware = int.from_bytes(payload[1:3], "little")
        hardware = payload[3]
        return LidarDeviceInfo(
            manufacturer="Slamtec",
            model=self._model_name(model_id),
            serial_number=payload[4:20].hex().upper(),
            firmware_version=f"{firmware >> 8}.{firmware & 0xFF:02d}",
            hardware_version=str(hardware),
        )

    def get_health(self) -> LidarHealth:
        payload = self._request(
            self._CMD_GET_DEVICE_HEALTH,
            expected_type=self._ANS_TYPE_DEVICE_HEALTH,
            expected_size=self._DEVICE_HEALTH_SIZE,
        )
        status = {
            0: LidarHealthStatus.OK,
            1: LidarHealthStatus.WARNING,
            2: LidarHealthStatus.ERROR,
        }.get(payload[0], LidarHealthStatus.UNKNOWN)
        return LidarHealth(
            status=status,
            error_code=int.from_bytes(payload[1:3], "little"),
        )

    def reset(self) -> None:
        self._require_connected()
        if self.is_scanning:
            self.stop_scan()
        self._send_command(self._CMD_RESET)
        if self.config.reset_wait_s:
            time.sleep(self.config.reset_wait_s)
        self._uart.reset_input_buffer()

    def start_scan(self) -> None:
        self._require_connected()
        if self.is_scanning:
            return
        self._uart.reset_input_buffer()
        self._send_command(self._CMD_SCAN)
        self._scanning = True
        try:
            descriptor = self._read_descriptor()
            if descriptor.send_mode != self._SEND_MODE_MULTIPLE:
                raise LidarProtocolError(
                    "Expected a streaming response, got send mode "
                    f"{descriptor.send_mode}"
                )
            if descriptor.data_type != self._ANS_TYPE_MEASUREMENT:
                raise LidarProtocolError(
                    "RPLIDAR C1 Standard mode expected response type "
                    f"0x{self._ANS_TYPE_MEASUREMENT:02X}, got "
                    f"0x{descriptor.data_type:02X}"
                )
            if descriptor.payload_size != self._MEASUREMENT_SIZE:
                raise LidarProtocolError(
                    f"Expected {self._MEASUREMENT_SIZE}-byte measurements, got "
                    f"{descriptor.payload_size}"
                )
        except Exception:
            try:
                self.stop_scan()
            except Exception:
                self._scanning = False
                _log.exception("Failed to stop RPLIDAR after scan startup error")
            raise

    def stop_scan(self) -> None:
        self._require_connected()
        if not self.is_scanning:
            return
        self._send_command(self._CMD_STOP)
        self._scanning = False
        if self.config.stop_wait_s:
            time.sleep(self.config.stop_wait_s)
        self._uart.reset_input_buffer()

    @staticmethod
    def _is_valid_measurement(data: bytes) -> bool:
        if len(data) != RPLidarC1._MEASUREMENT_SIZE:
            return False
        sync = data[0] & 0x01
        inverse_sync = (data[0] >> 1) & 0x01
        angle_and_check = int.from_bytes(data[1:3], "little")
        return sync != inverse_sync and bool(angle_and_check & 0x01)

    def _read_measurement_bytes(self) -> bytes:
        data = bytearray(self._read_exact(self._MEASUREMENT_SIZE, "scan measurement"))
        discarded = 0
        while not self._is_valid_measurement(bytes(data)):
            del data[0]
            data.extend(self._read_exact(1, "scan measurement resynchronization"))
            discarded += 1
            if discarded > self.config.max_resync_bytes:
                raise LidarProtocolError("Unable to synchronize scan measurements")
        return bytes(data)

    @staticmethod
    def _decode_measurement(data: bytes, timestamp: float) -> LidarMeasurement:
        sync_quality = data[0]
        angle_and_check = int.from_bytes(data[1:3], "little")
        distance_q2_mm = int.from_bytes(data[3:5], "little")
        raw_clockwise_angle_deg = (angle_and_check >> 1) / 64.0
        return LidarMeasurement(
            angle_deg=(-raw_clockwise_angle_deg) % 360.0,
            distance_m=distance_q2_mm / 4000.0,
            quality=sync_quality >> 2,
            start_of_scan=bool(sync_quality & 0x01),
            timestamp=timestamp,
        )

    def iter_measurements(self) -> Iterator[LidarMeasurement]:
        self._require_connected()
        if not self.is_scanning:
            raise LidarStateError("Call start_scan() before reading measurements")
        while self.is_scanning:
            data = self._read_measurement_bytes()
            yield self._decode_measurement(data, time.monotonic())
