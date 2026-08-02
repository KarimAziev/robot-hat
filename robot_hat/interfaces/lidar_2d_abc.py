from abc import ABC, abstractmethod
from types import TracebackType
from typing import Iterator, List, Optional, Type

from robot_hat.data_types.lidar import (
    LidarDeviceInfo,
    LidarHealth,
    LidarMeasurement,
    LidarScan,
)


class Lidar2DABC(ABC):
    """Generic synchronous interface for a planar range scanner."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @property
    @abstractmethod
    def is_scanning(self) -> bool:
        pass

    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def get_device_info(self) -> LidarDeviceInfo:
        pass

    @abstractmethod
    def get_health(self) -> LidarHealth:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass

    @abstractmethod
    def start_scan(self) -> None:
        pass

    @abstractmethod
    def stop_scan(self) -> None:
        pass

    @abstractmethod
    def iter_measurements(self) -> Iterator[LidarMeasurement]:
        """Yield measurements until scanning stops or communication fails."""

        pass

    def iter_scans(
        self,
        *,
        min_measurements: int = 1,
        max_scans: Optional[int] = None,
    ) -> Iterator[LidarScan]:
        """Group measurement markers into complete revolutions.

        Samples before the first start marker and the final partial revolution are
        intentionally discarded. This prevents consumers such as SLAM pipelines
        from mistaking partial data for a complete scan.
        """

        if min_measurements < 1:
            raise ValueError("min_measurements must be at least one")
        if max_scans is not None and max_scans < 1:
            raise ValueError("max_scans must be at least one or None")

        current: List[LidarMeasurement] = []
        synchronized = False
        yielded = 0

        for measurement in self.iter_measurements():
            if measurement.start_of_scan:
                if synchronized and len(current) >= min_measurements:
                    yield LidarScan(
                        measurements=tuple(current),
                        started_at=current[0].timestamp,
                        ended_at=current[-1].timestamp,
                    )
                    yielded += 1
                    if max_scans is not None and yielded >= max_scans:
                        return
                current = [measurement]
                synchronized = True
            elif synchronized:
                current.append(measurement)

    def __enter__(self) -> "Lidar2DABC":
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.disconnect()
