from robot_hat.mock.uart import MockUART
from robot_hat.mock.angular_position import MockAngularPosition
from robot_hat.mock.encoder import MockEncoder
from robot_hat.mock.imu import MockIMU
from robot_hat.mock.lidar import MockLidar2D
from robot_hat.mock.quadrature_counter import MockQuadratureCounterBackend
from robot_hat.mock.spi import MockAS5048ASPI, MockSPI

__all__ = [
    "MockAngularPosition",
    "MockEncoder",
    "MockIMU",
    "MockLidar2D",
    "MockQuadratureCounterBackend",
    "MockAS5048ASPI",
    "MockSPI",
    "MockUART",
]
