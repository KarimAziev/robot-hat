import logging
import os
from typing import Tuple, Union

from robot_hat.data_types.bus import BusType
from robot_hat.data_types.config.motor import (
    GPIODCMotorConfig,
    I2CDCMotorConfig,
    MotorConfig,
    PhaseMotorConfig,
)
from robot_hat.factories.pwm_factory import PWMFactory
from robot_hat.interfaces.motor_abc import MotorABC
from robot_hat.interfaces.pwm_driver_abc import PWMDriverABC
from robot_hat.motor.gpio_dc_motor import GPIODCMotor
from robot_hat.motor.i2c_dc_motor import I2CDCMotor
from robot_hat.motor.phase_motor import PhaseMotor
from robot_hat.pin import Pin

_log = logging.getLogger(__name__)


class MotorFactory:
    @classmethod
    def create_motor(
        cls,
        config: MotorConfig,
        bus: Union[BusType, None] = None,
        driver: Union[PWMDriverABC, None] = None,
        dir_pin: Union[Pin, None] = None,
    ) -> MotorABC:
        if isinstance(config, GPIODCMotorConfig):
            return cls.create_gpio_motor(config)
        elif isinstance(config, I2CDCMotorConfig):
            return cls.create_i2c_motor(config, bus=bus, driver=driver, dir_pin=dir_pin)
        elif isinstance(config, PhaseMotorConfig):
            return cls.create_phase_motor(config)
        else:
            message = f"Unsupported motor config type: {type(config).__name__}"
            _log.error("Passed unsupported motor config %s", motor_config)
            raise ValueError(message)

    @classmethod
    def create_motor_pair(
        cls,
        left_config: "MotorConfig",
        right_config: "MotorConfig",
        bus: Union[BusType, None] = None,
        driver: Union[PWMDriverABC, None] = None,
        dir_pin: Union[Pin, None] = None,
    ) -> Tuple[MotorABC, MotorABC]:
        return (
            MotorFactory.create_motor(
                left_config, bus=bus, driver=driver, dir_pin=dir_pin
            ),
            MotorFactory.create_motor(
                right_config, bus, driver=driver, dir_pin=dir_pin
            ),
        )

    @classmethod
    def create_phase_motor(
        cls,
        config: PhaseMotorConfig,
    ) -> MotorABC:
        is_mock = os.getenv("GPIOZERO_PIN_FACTORY") == "mock"
        _log.debug("Creating PhaseMotor with config: %s", config)

        if is_mock and config.pwm:
            _log.warning(
                "Disabling PWM value from config because the gpiozero mock implementation does not support PWM "
            )

        pwm_value = (
            False  # disable pwm for the gpiozero.mock implementation
            if is_mock
            else config.pwm
        )

        return PhaseMotor(
            phase_pin=config.phase_pin,
            enable_pin=config.enable_pin,
            pwm=pwm_value,
            calibration_direction=config.calibration_direction,
            max_speed=config.max_speed,
            name=config.name,
        )

    @classmethod
    def create_gpio_motor(cls, config: GPIODCMotorConfig) -> MotorABC:
        is_mock = os.getenv("GPIOZERO_PIN_FACTORY") == "mock"
        _log.debug("Initializing GPIO DC motor %s", config)

        if is_mock and config.pwm:
            _log.warning(
                "Disabling PWM value from config because the gpiozero mock implementation does not support PWM "
            )

        pwm_value = (
            False  # disable pwm for the gpiozero.mock implementation
            if is_mock
            else config.pwm
        )
        return GPIODCMotor(
            forward_pin=config.forward_pin,
            backward_pin=config.backward_pin,
            pwm_pin=config.enable_pin,
            calibration_direction=config.calibration_direction,
            max_speed=config.max_speed,
            name=config.name,
            pwm=pwm_value,
        )

    @classmethod
    def create_i2c_motor(
        cls,
        config: I2CDCMotorConfig,
        bus: Union[BusType, None] = None,
        driver: Union[PWMDriverABC, None] = None,
        dir_pin: Union[Pin, None] = None,
    ) -> MotorABC:
        _log.debug("Initializng I2C motor %s", config)

        driver = driver or PWMFactory.create_pwm_driver(
            config.driver,
            bus=bus,
        )
        dir_pin = dir_pin or Pin(config.dir_pin)

        return I2CDCMotor(
            channel=config.channel,
            driver=driver,
            frequency=config.driver.freq,
            dir_pin=dir_pin,
            calibration_direction=config.calibration_direction,
            max_speed=config.max_speed,
        )
