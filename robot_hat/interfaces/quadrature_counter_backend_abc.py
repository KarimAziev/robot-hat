"""Hardware-independent quadrature counter backend contract."""

from abc import ABC, abstractmethod

from robot_hat.data_types.quadrature import QuadratureCounterSnapshot


class QuadratureCounterBackendABC(ABC):
    """Atomic signed counter supplied by an electrical edge-capture backend.

    Implementations may use callbacks, a hardware timer, a co-processor, a
    kernel interface, or a remote motor controller. Initialization is explicit;
    importing a backend must not access hardware. Implementations must make
    ``read_snapshot`` and ``reset`` atomic relative to edge processing.

    A backend owns and closes resources it creates. Injected or shared resources
    remain open unless ownership was explicitly transferred to that backend.
    ``close`` must be idempotent. Reads before initialization and after close
    must raise typed encoder lifecycle errors.
    """

    @abstractmethod
    def initialize(self) -> None:
        """Initialize resources and begin counting; repeated calls are safe."""
        pass

    @abstractmethod
    def read_snapshot(self) -> QuadratureCounterSnapshot:
        """Return one atomic cumulative count, timestamp, and diagnostic set."""
        pass

    @abstractmethod
    def reset(self, count: int = 0) -> None:
        """Atomically set the signed count without changing electrical phase."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Stop counting and release only owned resources; safe more than once."""
        pass


__all__ = ["QuadratureCounterBackendABC"]
