"""Raw both-edge digital input implemented with GPIO Zero."""

from typing import TYPE_CHECKING, Union

from robot_hat.exceptions import EncoderClosedError, EncoderNotInitializedError
from robot_hat.interfaces.digital_edge_input_abc import (
    DigitalEdgeCallback,
    DigitalEdgeInputABC,
)


PinIdentifier = Union[int, str]

if TYPE_CHECKING:
    from gpiozero import DigitalInputDevice


class GPIOZeroDigitalEdgeInput(DigitalEdgeInputABC):
    """GPIO Zero input with no bounce filtering and callbacks on both edges.

    Construction stores configuration only. The GPIO device is created by
    :meth:`initialize`, avoiding hardware access during import or object graph
    construction. GPIO Zero's logical active state may invert a pulled-up input;
    quadrature direction is unchanged when both channels use the same settings.
    """

    def __init__(
        self,
        pin: PinIdentifier,
        *,
        pull_up: bool = False,
        active_state: bool | None = None,
    ) -> None:
        if isinstance(pin, bool) or not isinstance(pin, (int, str)):
            raise TypeError("pin must be an integer or string")
        if not isinstance(pull_up, bool):
            raise TypeError("pull_up must be a bool")
        if not isinstance(active_state, (bool, type(None))):
            raise TypeError("active_state must be bool or None")
        self._pin = pin
        self._pull_up = pull_up
        self._active_state = active_state
        self._device: DigitalInputDevice | None = None
        self._callback: DigitalEdgeCallback | None = None
        self._closed = False

    def initialize(self) -> None:
        if self._closed:
            raise EncoderClosedError("GPIOZeroDigitalEdgeInput is closed")
        if self._device is not None:
            return
        from gpiozero import DigitalInputDevice

        self._device = DigitalInputDevice(
            self._pin,
            pull_up=self._pull_up,
            active_state=self._active_state,
            bounce_time=None,
        )
        self._apply_callback()

    def read(self) -> bool:
        return bool(self._require_device().value)

    def set_edge_callback(self, callback: DigitalEdgeCallback | None) -> None:
        if callback is not None and not callable(callback):
            raise TypeError("callback must be callable or None")
        if self._closed:
            raise EncoderClosedError("GPIOZeroDigitalEdgeInput is closed")
        self._callback = callback
        if self._device is not None:
            self._apply_callback()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        device = self._device
        self._device = None
        self._callback = None
        if device is not None:
            device.when_activated = None
            device.when_deactivated = None
            device.close()

    def _apply_callback(self) -> None:
        device = self._require_device()
        device.when_activated = self._callback
        device.when_deactivated = self._callback

    def _require_device(self) -> "DigitalInputDevice":
        if self._closed:
            raise EncoderClosedError("GPIOZeroDigitalEdgeInput is closed")
        if self._device is None:
            raise EncoderNotInitializedError(
                "call initialize() before reading the digital edge input"
            )
        return self._device


__all__ = ["GPIOZeroDigitalEdgeInput", "PinIdentifier"]
