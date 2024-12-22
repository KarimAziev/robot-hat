class ADCAddressNotFound(Exception):
    """
    Exception raised when ADC address is not found.
    """

    pass


class InvalidPin(ValueError):
    """
    Exception raised when pin not found.
    """

    pass


class InvalidPinName(InvalidPin):
    """
    Exception raised when pin name is not found.
    """

    pass


class InvalidPinNumber(InvalidPin):
    """
    Exception raised when pin number is not found.
    """

    pass


class InvalidPinMode(ValueError):
    """
    Exception raised when pin mode is invalid.
    """

    pass


class InvalidPinPull(ValueError):
    """
    Exception raised when pull mode is invalid.
    """

    pass


class InvalidPinInterruptTrigger(ValueError):
    """
    Exception raised when Interrupt Pin triggers the trigger is not valid.
    """

    pass


class InvalidServoAngle(ValueError):
    """
    Exception raised when Interrupt Pin triggers the trigger is not valid.
    """

    pass
