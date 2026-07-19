from typing import List

from robot_hat.data_types.uart import USBUARTDevice, USBUARTSelector
from robot_hat.exceptions import UARTPortAmbiguousError, UARTPortNotFoundError


def list_usb_uart_devices() -> List[USBUARTDevice]:
    """Return serial ports with the USB metadata exposed by the OS.

    Native UARTs may also appear with empty USB identifiers. Keeping them in the
    result makes this useful for diagnosing both ``/dev/ttyUSB*`` adapters and
    stable ``/dev/serial/by-id/*`` or native UART paths.
    """

    from serial.tools import list_ports

    return [
        USBUARTDevice(
            port=port.device,
            description=port.description,
            hardware_id=port.hwid,
            vendor_id=port.vid,
            product_id=port.pid,
            serial_number=port.serial_number,
            manufacturer=port.manufacturer,
            product=port.product,
            location=port.location,
        )
        for port in list_ports.comports()
    ]


def _contains_casefold(value: str | None, expected: str | None) -> bool:
    if expected is None:
        return True
    return value is not None and expected.casefold() in value.casefold()


def find_usb_uart_device(selector: USBUARTSelector) -> USBUARTDevice:
    """Resolve a selector to exactly one serial device."""

    matches = [
        device
        for device in list_usb_uart_devices()
        if (selector.vendor_id is None or device.vendor_id == selector.vendor_id)
        and (selector.product_id is None or device.product_id == selector.product_id)
        and (
            selector.serial_number is None
            or device.serial_number == selector.serial_number
        )
        and _contains_casefold(device.manufacturer, selector.manufacturer)
        and _contains_casefold(device.product, selector.product)
    ]
    if not matches:
        raise UARTPortNotFoundError(f"No UART port matches {selector!r}")
    if len(matches) > 1:
        ports = ", ".join(device.port for device in matches)
        raise UARTPortAmbiguousError(
            f"UART selector {selector!r} matches multiple ports: {ports}"
        )
    return matches[0]
