class ADCAddressNotFound(Exception):
    """
    Exception raised when the ADC address is not found.
    """

    pass


class InvalidPin(ValueError):
    """
    Exception raised when the specified pin is invalid or not found.
    """

    pass


class InvalidPinName(InvalidPin):
    """
    Exception raised when the specified pin name is invalid or not found.
    """

    pass


class InvalidPinNumber(InvalidPin):
    """
    Exception raised when the specified pin number is invalid or not found.
    """

    pass


class InvalidPinMode(ValueError):
    """
    Exception raised when the specified pin mode is invalid.
    """

    pass


class InvalidPinPull(ValueError):
    """
    Exception raised when the specified pull mode is invalid.
    """

    pass


class InvalidPinInterruptTrigger(ValueError):
    """
    Exception raised when the specified interrupt trigger for the pin is invalid.
    """

    pass


class InvalidServoAngle(ValueError):
    """
    Exception raised when the specified servo angle is invalid.
    """

    pass


class InvalidChannel(ValueError):
    """
    Exception raised when the specified channel is invalid.
    """

    pass


class InvalidChannelName(InvalidChannel):
    """
    Exception raised when the specified channel name, provided as a string, is invalid.
    """

    pass


class InvalidChannelNumber(InvalidChannel):
    """
    Exception raised when the specified channel number, provided as an integer, is invalid.
    """

    pass


class UltrasonicEchoPinError(RuntimeError):
    """
    Exception raised when the echo pin is not properly initialized.
    """

    pass


class GrayscaleTypeError(TypeError):
    """
    Exception raised for errors in the grayscale module.
    """

    pass


class FileDBValidationError(ValueError):
    """
    Exception raised when there is an attempt to set an invalid config key-value pair.
    """

    pass


class MotorValidationError(ValueError):
    """
    Exception raised when there is an attempt to set an invalid motor parameter.
    """

    pass


class InvalidCalibrationModeError(Exception):
    """
    Raised when an invalid calibration mode is provided to the ServoService.
    """

    def __init__(self, mode, message="Invalid calibration mode provided."):
        super().__init__(f"{message} Received: {mode}")
        self.mode = mode
