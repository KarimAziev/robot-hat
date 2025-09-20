"""
Factory helpers for constructing MotorABC implementations from configuration dataclasses.
"""

import logging
import os
from typing import Tuple, Union

from robot_hat.data_types.bus import BusType
from robot_hat.data_types.config.motor import (
    GPIODCMotorConfig,
    I2CDCMotorConfig,
    MotorConfigType,
    PhaseMotorConfig,
)
from robot_hat.exceptions import UnsupportedMotorConfigError
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
        config: MotorConfigType,
        bus: Union[BusType, None] = None,
        driver: Union[PWMDriverABC, None] = None,
        dir_pin: Union[Pin, None] = None,
    ) -> MotorABC:
        """
        Create a motor instance from a provided config.

        It supports three motor configuration types:

        - I2CDCMotorConfig: a DC motor driven by a PWM driver chip on an I²C bus.
        - GPIODCMotorConfig: a DC motor controlled directly via GPIO pins.
        - PhaseMotorConfig: a phase/enable style motor controller (single digital phase pin
          + optional PWM enable pin).

        Parameters
        ----------
        config: A configuration dataclass instance describing the motor to create.
        bus: Optional I²C bus hint or handle used when constructing PWM drivers for I²C-driven motors.
             Accepted values:
             - int: the platform I²C bus number (e.g. 1 on a Raspberry Pi).
             - SMBusABC-compatible object: an already-opened SMBus-like object. When provided, the factory will
               pass this object to PWMFactory.create_pwm_driver so the PWM
               driver can reuse the same bus instance.
             - None: no explicit bus supplied; the PWMFactory will use the bus
               defined in the PWMDriverConfig or its own default behavior.
             Notes:
             - If an explicit PWM driver is provided via the driver parameter, the bus argument is ignored.
        driver: Optional already-constructed PWM driver to use for I²C motors. If omitted, the
            factory will call PWMFactory.create_pwm_driver with the configuration from `config`.
        dir_pin: Optional Pin object to use as the direction pin for I²C motors. If None, a Pin will
            be constructed from the `dir_pin` value in I2CDCMotorConfig.

        Returns
        -------
        MotorABC
            The constructed motor implementation (GPIODCMotor, I2CDCMotor, or PhaseMotor).

        Raises
        ------
        UnsupportedMotorConfigError: If an unsupported config type is passed.

        Examples
        --------
        # Example 1: I2C-driven DC motor using an explicit PWM driver instance
        --------
        ```python
        from robot_hat import I2CDCMotorConfig, MotorFactory, PWMDriverConfig, PWMFactory

        driver_cfg = PWMDriverConfig(
            name="Sunfounder", bus=1, frame_width=20000, freq=50, address=0x14
        )
        driver = PWMFactory.create_pwm_driver(driver_cfg, bus=1)

        i2c_cfg = I2CDCMotorConfig(
            calibration_direction=1,
            name="right_motor",
            max_speed=100,
            driver=driver_cfg,
            channel="P13",
            dir_pin="D5",
        )

        i2c_motor = MotorFactory.create_motor(i2c_cfg, driver=driver)

        ```


        # Example 2: GPIO-driven DC motor
        --------
        ```python
        from robot_hat import GPIODCMotorConfig, MotorFactory

        motor = MotorFactory.create_motor(
            config=GPIODCMotorConfig(
                calibration_direction=1,
                name="left_motor",
                max_speed=100,
                forward_pin=6,
                backward_pin=13,
                enable_pin=12,
                pwm=True,
            )
        )
        ```

        # Example 3: Phase/enable motor
        --------
        ```python
        from robot_hat import MotorFactory, PhaseMotorConfig

        cfg_phase = PhaseMotorConfig(
            calibration_direction=-1,
            name="lifter",
            max_speed=100,
            phase_pin=17,
            pwm=True,
            enable_pin=27,
        )
        motor_phase = MotorFactory.create_motor(cfg_phase)
        ```


        """
        if isinstance(config, GPIODCMotorConfig):
            return cls.create_gpio_motor(config)
        elif isinstance(config, I2CDCMotorConfig):
            return cls.create_i2c_motor(config, bus=bus, driver=driver, dir_pin=dir_pin)
        elif isinstance(config, PhaseMotorConfig):
            return cls.create_phase_motor(config)
        else:
            message = f"Unsupported motor config type: {type(config).__name__}"
            _log.error(
                "Passed unsupported motor config %s %s",
                {type(config).__name__},
                config,
            )
            raise UnsupportedMotorConfigError(message)

    @classmethod
    def create_motor_pair(
        cls,
        left_config: "MotorConfigType",
        right_config: "MotorConfigType",
        bus: Union[BusType, None] = None,
        driver: Union[PWMDriverABC, None] = None,
        dir_pin: Union[Pin, None] = None,
    ) -> Tuple[MotorABC, MotorABC]:
        """
        Create a pair of motors (left, right) from the provided configs.

        This is a convenience wrapper around two calls to create_motor.

        Parameters
        ----------
        left_config: Configuration for the left motor.
        right_config: Configuration for the right motor.
        bus, driver, dir_pin: Same semantics as MotorFactory.create_motor and are passed through to both
            underlying create_motor calls.

        Returns
        -------
        A tuple with left and right motor instances.

        Example
        -------
        left_motor, right_motor = MotorFactory.create_motor_pair(left_cfg, right_cfg, driver=driver)
        """
        return (
            cls.create_motor(left_config, bus=bus, driver=driver, dir_pin=dir_pin),
            cls.create_motor(right_config, bus, driver=driver, dir_pin=dir_pin),
        )

    @classmethod
    def create_phase_motor(
        cls,
        config: PhaseMotorConfig,
    ) -> MotorABC:
        """
        Construct a Phase/Enable motor.

        Behavior notes:
        - If GPIOZERO_PIN_FACTORY environment variable equals "mock", PWM support will be disabled
          (pwm will be set to False) because the gpiozero mock does not implement PWM.
        """
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
        """
        Construct a GPIODCMotor from GPIODCMotorConfig.

        Behavior notes:
        - If GPIOZERO_PIN_FACTORY environment variable equals "mock", PWM support will be disabled
          (pwm will be set to False) because the gpiozero mock does not implement PWM.

        Parameters
        ----------
        config: Configuration describing forward/backward pins, optional enable pin and PWM usage.

        Returns
        -------
        A GPIODCMotor instance configured according to `config`.

        Example
        -------
        ```python
        from robot_hat import GPIODCMotorConfig, MotorFactory

        motor = MotorFactory.create_gpio_motor(
            config=GPIODCMotorConfig(
                calibration_direction=1,
                name="left_motor",
                max_speed=100,
                forward_pin=6,
                backward_pin=13,
                enable_pin=12,
                pwm=True,
            )
        )
        ```
        """
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
        """
        Construct an I2CDCMotor from I2CDCMotorConfig.

        This method will use the provided `driver` if given. If `driver` is None, it will construct PWM driver from configuration embedded in `config`.

        The `dir_pin` parameter may be either a Pin instance or None; when None, a Pin will be
        constructed from config.dir_pin.

        Parameters
        ----------
        config: Configuration describing the PWM driver config, PWM channel and direction pin.
        bus: Optional I²C bus hint or handle used when constructing PWM drivers for I²C-driven motors.
        driver: Optional already-constructed PWM driver to use.
        dir_pin: Pin | None
            Optional Pin instance to use as the motor direction pin.

        Returns
        -------
        I2CDCMotor
            An I2CDCMotor instance configured according to `config`.

        Example
        -------
        ```python
        from robot_hat import I2CDCMotorConfig, MotorFactory, PWMDriverConfig, PWMFactory

        pwm_cfg = PWMDriverConfig(
            name="PCA9685", bus=1, frame_width=20000, freq=50, address=0x40
        )
        driver = PWMFactory.create_pwm_driver(pwm_cfg, bus=1)

        i2c_cfg = I2CDCMotorConfig(
            calibration_direction=1,
            name="right_motor",
            max_speed=100,
            driver=pwm_cfg,
            channel="P13",
            dir_pin="D5",
        )

        motor = MotorFactory.create_i2c_motor(i2c_cfg, driver=driver)

        ```
        """
        _log.debug("Initializing I2C motor %s", config)

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
