from typing import Literal, Union

from robot_hat.data_types.config.motor import MotorDirection

MotorZeroDirection = Literal[0]

MotorServiceDirection = Union[MotorDirection, MotorZeroDirection]
