"""
A module to manage the pins and perform various operations like:
- setting up pin modes
- reading or writing values to the pin
- configuring interrupts.

Types of Pins
--------------
- Power Pins: Provide a constant voltage supply to power the board and external components.
- Ground Pins (GND): Serve as the reference point for the circuit and complete the electrical circuit.
- GPIO Pins (General-Purpose Input/Output): Configurable pins used for digital input or output to interact with external devices.
"""

import logging
from typing import Callable, ClassVar, Dict, Literal, Optional, Union, overload

from robot_hat.exceptions import (
    InvalidPin,
    InvalidPinInterruptTrigger,
    InvalidPinMode,
    InvalidPinName,
    InvalidPinNumber,
    InvalidPinPull,
)
from robot_hat.pin_descriptions import pin_descriptions

logger = logging.getLogger(__name__)


class Pin(object):
    """
    A class to manage the pins and perform various operations like setting up
    pin modes, reading or writing values to the pin, and configuring interrupts.

    Pin Modes:
    --------------
    - OUT (0x01): Configure the pin as an output pin.
    - IN (0x02): Configure the pin as an input pin.

    Internal Pull-Up/Pull-Down Resistors:
    --------------
    - PULL_UP (0x11): Enable internal pull-up resistor.
    - PULL_DOWN (0x12): Enable internal pull-down resistor.
    - PULL_NONE (None): No internal pull-up or pull-down resistor.

    Interrupt Triggers:
    --------------
    - IRQ_FALLING (0x21): Interrupt on falling edge.
    - IRQ_RISING (0x22): Interrupt on rising edge.
    - IRQ_RISING_FALLING (0x23): Interrupt on both rising and falling edges.
    """

    DEFAULT_PIN_MAPPING: ClassVar[Dict[str, int]] = {
        "D0": 17,
        "D1": 4,  # Changed
        "D2": 27,
        "D3": 22,
        "D4": 23,  # Left motor direction PIN
        "D5": 24,  # Right motor direction PIN
        "D6": 25,  # Removed
        "D7": 4,  # Removed
        "D8": 5,  # Removed
        "D9": 6,
        "D10": 12,
        "D11": 13,
        "D12": 19,
        "D13": 16,
        "D14": 26,
        "D15": 20,
        "D16": 21,
        "SW": 25,  # Changed
        "USER": 25,
        "LED": 26,
        "BOARD_TYPE": 12,
        "RST": 16,
        "BLEINT": 13,
        "BLERST": 20,
        "MCURST": 5,  # Changed
        "CE": 8,
    }

    OUT = 0x01
    """Pin mode output"""
    IN = 0x02
    """Pin mode input"""

    PULL_UP = 0x11
    """Pin internal pull up"""
    PULL_DOWN = 0x12
    """Pin internal pull down"""
    PULL_NONE = None
    """Pin internal pull none"""

    IRQ_FALLING = 0x21
    """Pin interrupt falling"""
    IRQ_RISING = 0x22
    """Pin interrupt rising"""
    IRQ_RISING_FALLING = 0x23
    """Pin interrupt both rising and falling"""

    def __init__(
        self,
        pin: Union[int, str],
        mode: Optional[int] = None,
        pull: Optional[int] = None,
        pin_dict: Dict[str, int] = DEFAULT_PIN_MAPPING,
        *args,
        **kwargs,
    ):
        """
        Initialize a GPIO Pin.

        Args:
        - `pin`: Pin identifier, either as a GPIO pin number (int) or a named string.
        - `mode`: Mode of the pin, either `Pin.OUT` for output or `Pin.IN` for input. Default is None.
        - `pull`: Configure internal pull-up or pull-down resistors.
        - `pin_dict`: The dictionary of pin names and corresponding pin numbers defaults to the `DEFAULT_PIN_MAPPING`.

        Args:
            pin (Union[int, str]): Pin identifier, either as a GPIO pin number (int) or a named string.

        Raises:
        --------------
        - `InvalidPinName`: If the provided string pin name does not exist in the dictionary.
        - `InvalidPinNumber`: If the provided integer pin number does not match any entries in the dictionary.
        - `InvalidPin`: If the input pin type is neither an integer nor a string.
        - `InvalidPinMode`: If the mode is not valid.
        - `InvalidPinPull`: If pull is not valid.
        """
        super().__init__(*args, **kwargs)

        # Parse pin
        self.dict = pin_dict
        self._setup_pin_number(pin)

        self._value = 0
        self.gpio = None
        self.setup(mode, pull)

        mode_str = "None" if mode is None else "OUT" if mode == self.OUT else "INPUT"
        pull_str = (
            "without internal resistor"
            if pull is None
            else (
                "with PULL-UP resistor"
                if pull == self.PULL_UP
                else "with PULL-DOWN resistor"
            )
        )
        pull_hex = "None" if pull is None else f"0x{pull:02X}"

        self.descr = " ".join(
            [
                self.name(),
                (
                    pin_descriptions.get(self._board_name, "")
                    if pin_dict is self.DEFAULT_PIN_MAPPING
                    else ""
                ),
                self._board_name,
            ]
        )

        logger.debug(
            "Initted [%s], mode: %s (0x%s:02X) %s (%s)",
            self.descr,
            mode_str,
            self._pin_num,
            pull_str,
            pull_hex,
        )

    def _setup_pin_number(self, pin: Union[int, str]) -> None:
        """
        Determines and sets up the GPIO pin number based on the input pin
        identifier (integer or string).

        Args:
            pin (Union[int, str]): Pin identifier, either as a GPIO pin number (int) or a named string.

        Raises:
        --------------
        - `InvalidPinName`: If the provided string pin name does not exist in the dictionary.
        - `InvalidPinNumber`: If the provided integer pin number does not match any entries in the dictionary.
        - `InvalidPin`: If the input pin type is neither an integer nor a string.

        """
        if isinstance(pin, str):
            pin_num = self.dict.get(pin)
            if pin_num is None:
                msg = f"Pin '{pin}' is not found in {self.dict.keys()}"
                logger.error(msg)
                raise InvalidPinName(msg)
            self._board_name = pin
            self._pin_num = pin_num
        elif isinstance(pin, int):
            names = [i for i in self.dict if self.dict[i] == pin]
            length = len(names)
            if length <= 0:
                msg = f"Pin number is not found in {self.dict.values}"
                raise InvalidPinNumber(pin)
            name = names[0]
            if length > 1:
                msg = f"Pin number is not found in {self.dict.values}"
                logger.warning(
                    f"Multiple pins found for pin '{pin}': {', '.join(names)}  using the {name}"
                )
            self._board_name = name
            self._pin_num = pin
        else:
            msg = f'Invalid PIN: "{pin}"'
            logger.error(msg)
            raise InvalidPin(msg)

    @property
    def dict(self) -> Dict[str, int]:
        return self._dict

    @dict.setter
    def dict(self, value: Dict[str, int]):
        self._dict = value
        return self._dict

    def close(self) -> None:
        """
        Close the GPIO pin.
        """
        logger.debug(
            "[%s]: Closing %s",
            self.descr,
            self.gpio,
        )
        if self.gpio:
            self.gpio.close()

    def deinit(self) -> None:
        """
        Deinitialize the GPIO pin and its factory.
        """
        if self.gpio:
            self.gpio.close()
            pin_factory = self.gpio.pin_factory
            if pin_factory is not None:
                pin_factory.close()

    def setup(self, mode, pull: Optional[int] = None) -> None:
        """
        Setup the GPIO pin with a specific mode and optional pull-up/down resistor configuration.

        Args:
        --------------
        - mode (int): Mode of the pin (`Pin.OUT` for output, `Pin.IN` for input). Default is None.
        - pull (Optional[int]): Configure pull-up/down resistors (`Pin.PULL_UP`, `Pin.PULL_DOWN`, `Pin.PULL_NONE`). Default is None.

        Raises:
        --------------
        - `InvalidPinMode`: If the mode is not valid.
        - `InvalidPinPull`: If pull is not valid.
        """
        if mode in [None, self.OUT, self.IN]:
            self._mode = mode
        else:
            msg = f"mode param error, should be None, Pin.OUT, Pin.IN"
            logger.error(msg)
            raise InvalidPinMode(msg)

        if pull in [self.PULL_NONE, self.PULL_DOWN, self.PULL_UP]:
            self._pull = pull
        else:
            msg = f"pull param error, should be None, Pin.PULL_NONE, Pin.PULL_DOWN, Pin.PULL_UP"
            logger.error(msg)
            raise InvalidPinPull(msg)

        if self.gpio != None:
            if self.gpio.pin != None:
                self.gpio.close()

        if mode in [None, self.OUT]:
            from gpiozero import OutputDevice

            self.gpio = OutputDevice(self._pin_num)
        else:
            from gpiozero import InputDevice

            if pull in [self.PULL_UP]:
                self.gpio = InputDevice(self._pin_num, pull_up=True)
            else:
                self.gpio = InputDevice(self._pin_num, pull_up=False)

    def __call__(self, value: Union[Literal[0], Literal[1]]) -> int:
        """
        Set or get the value of the GPIO pin.

        Args:
            value (int): Value to set the pin (high=1, low=0).

        Returns:
            int: Value of the pin (0 or 1).
        """
        return self.value(value)

    @overload
    def value(self, value: None = None) -> Optional[int]:
        """
        Overload for getting the value of the GPIO pin.
        When no value is passed, the method will return the current state of the pin.
        """
        ...

    @overload
    def value(self, value: Literal[0]) -> int:
        """
        Overload for setting the value of the GPIO pin to low (0).
        """
        ...

    @overload
    def value(self, value: Literal[1]) -> int:
        """
        Overload for setting the value of the GPIO pin to high (1).
        """
        ...

    def value(self, value: Optional[int] = None) -> Optional[int]:
        """
        Set or get the value of the GPIO pin.

        Args:
            value (Optional[int]): Value to set the pin (high=1, low=0). Leave empty to get the current value.

        Returns:
            int: Value of the pin (0 or 1) if value is not provided.

        Raises:
            ValueError: If the mode is not valid or the pin is not properly initialized.
        """
        if value == None:
            if self._mode in [None, self.OUT]:
                self.setup(self.IN)
            result: Optional[int] = self.gpio.value if self.gpio else None
            logger.debug(
                "read pin %s: %s",
                self.gpio.pin if self.gpio else None,
                result,
            )
            return result
        else:
            if self._mode in [self.IN]:
                self.setup(self.OUT)
            if bool(value):
                res = 1
                from gpiozero import OutputDevice

                if isinstance(self.gpio, OutputDevice):
                    self.gpio.on()
            else:
                res = 0
                from gpiozero import OutputDevice

                if isinstance(self.gpio, OutputDevice):
                    self.gpio.off()
            return res

    def on(self) -> int:
        """
        Set the pin value to high (1).

        Returns:
            int: The set pin value (1).
        """
        return self.value(1)

    def off(self) -> int:
        """
        Set the pin value to low (0).

        Returns:
            int: The set pin value (0).
        """
        return self.value(0)

    def high(self) -> int:
        """
        Alias for `on()` - Set the pin value to high (1).

        Returns:
            int: The set pin value (1).
        """
        return self.on()

    def low(self) -> int:
        """
        Alias for `off()` - Set the pin value to low (0).

        Returns:
            int: The set pin value (0).
        """
        return self.off()

    def irq(
        self,
        handler: Callable[[], None],
        trigger: int,
        bouncetime=200,
        pull: Optional[int] = None,
    ) -> None:
        """
        Set the pin interrupt handler.

        Args:
        - handler (function): Interrupt handler callback function.
        - trigger (int): Interrupt trigger (`Pin.IRQ_FALLING`, `Pin.IRQ_RISING`, `Pin.IRQ_RISING_FALLING`).
        - bouncetime (int): Interrupt debounce time in milliseconds. Default is 200.
        - pull (Optional[int]): Configure pull-up/down resistors (`Pin.PULL_UP`, `Pin.PULL_DOWN`, `Pin.PULL_NONE`). Default is None.

        Raises:
        - InvalidPinInterruptTrigger: If the trigger is not valid.
        - InvalidPinPull: If the pull parameters are not valid.
        """
        from gpiozero import Button

        if trigger not in [self.IRQ_FALLING, self.IRQ_RISING, self.IRQ_RISING_FALLING]:
            raise InvalidPinInterruptTrigger(
                "trigger param error, should be Pin.IRQ_FALLING, Pin.IRQ_RISING, Pin.IRQ_RISING_FALLING"
            )

        if pull in [self.PULL_NONE, self.PULL_DOWN, self.PULL_UP]:
            self._pull = pull
            if pull == self.PULL_UP:
                _pull_up = True
            else:
                _pull_up = False
        else:
            raise InvalidPinPull(
                "pull param error, should be Pin.PULL_NONE, Pin.PULL_DOWN, Pin.PULL_UP"
            )

        pressed_handler = None
        released_handler = None

        if not isinstance(self.gpio, Button):
            if self.gpio != None:
                self.gpio.close()
            self.gpio = Button(
                pin=self._pin_num,
                pull_up=_pull_up,
                bounce_time=float(bouncetime / 1000),
            )
            self._bouncetime = bouncetime
        else:
            if bouncetime != self._bouncetime:
                pressed_handler = self.gpio.when_activated
                released_handler = self.gpio.when_deactivated
                self.gpio.close()
                self.gpio = Button(
                    pin=self._pin_num,
                    pull_up=_pull_up,
                    bounce_time=float(bouncetime / 1000),
                )
                self._bouncetime = bouncetime

        if trigger in [None, self.IRQ_FALLING]:
            pressed_handler = handler
        elif trigger in [self.IRQ_RISING]:
            released_handler = handler
        elif trigger in [self.IRQ_RISING_FALLING]:
            pressed_handler = handler
            released_handler = handler

        if pressed_handler is not None and self.gpio is not None:
            self.gpio.when_pressed = pressed_handler
        if released_handler is not None and self.gpio is not None:
            self.gpio.when_released = released_handler

    def name(self) -> str:
        """
        Get the GPIO pin name.

        Returns:
            The GPIO pin name.
        """
        return f"GPIO{self._pin_num}"
