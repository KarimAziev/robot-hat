import unittest

from robot_hat.drivers.angle.as5048a import AS5048ADiagnostics
from robot_hat.exceptions import EncoderMagnetError, EncoderNotInitializedError
from robot_hat.sensors.encoder.as5048a_encoder import AS5048AEncoder


GOOD_DIAGNOSTICS = AS5048ADiagnostics(
    offset_compensation_finished=True,
    cordic_overflow=False,
    magnet_too_strong=False,
    magnet_too_weak=False,
    automatic_gain_control=128,
    raw=0x180,
)


class FakeAS5048A:
    def __init__(
        self,
        raw_angles: list[int],
        diagnostics: AS5048ADiagnostics = GOOD_DIAGNOSTICS,
    ) -> None:
        self.raw_angles = iter(raw_angles)
        self.diagnostics = diagnostics
        self.closed = False

    def read_diagnostics(self) -> AS5048ADiagnostics:
        return self.diagnostics

    def read_raw_angle(self) -> int:
        return next(self.raw_angles)

    def read_angle_degrees(self) -> float:
        return self.read_raw_angle() * 360.0 / 16_384

    def close(self) -> None:
        self.closed = True


class TestAS5048AEncoder(unittest.TestCase):
    def test_requires_initialize_and_unwraps_both_boundary_directions(self) -> None:
        sensor = FakeAS5048A([16_380, 3, 16_382])
        encoder = AS5048AEncoder(
            sensor=sensor,
            monotonic_ns=iter([0, 10, 20]).__next__,
        )
        with self.assertRaises(EncoderNotInitializedError):
            encoder.read_sample()

        encoder.initialize()

        self.assertEqual(encoder.ticks_per_revolution, 16_384)
        self.assertEqual(encoder.read_sample().ticks, 7)
        self.assertEqual(encoder.read_sample().ticks, 2)

    def test_inverts_resets_and_rebaselines_after_long_gap(self) -> None:
        sensor = FakeAS5048A([100, 110, 900, 905])
        encoder = AS5048AEncoder(
            sensor=sensor,
            monotonic_ns=iter([0, 10, 200, 210]).__next__,
            invert_direction=True,
            max_sample_gap_ns=100,
            max_abs_speed_rps=None,
        )
        encoder.initialize()
        self.assertEqual(encoder.read_sample().ticks, -10)
        encoder.reset(50)
        with self.assertLogs(
            "robot_hat.sensors.encoder.as5048a_encoder", level="WARNING"
        ):
            self.assertEqual(encoder.read_sample().ticks, 50)
        self.assertEqual(encoder.read_sample().ticks, 45)
        self.assertEqual(encoder.read_health().invalid_transitions, 1)

    def test_rejects_magnetic_fault_and_recovers_by_rebaselining(self) -> None:
        sensor = FakeAS5048A([100, 120, 125])
        encoder = AS5048AEncoder(
            sensor=sensor,
            monotonic_ns=iter([0, 10, 20]).__next__,
        )
        encoder.initialize()
        sensor.diagnostics = AS5048ADiagnostics(
            True, False, False, True, 255, (1 << 11) | (1 << 8)
        )

        with self.assertRaises(EncoderMagnetError):
            encoder.read_sample()

        sensor.diagnostics = GOOD_DIAGNOSTICS
        self.assertEqual(encoder.read_sample().ticks, 0)
        self.assertEqual(encoder.read_sample().ticks, 5)
        self.assertEqual(encoder.read_health().invalid_transitions, 1)

    def test_injected_sensor_is_not_owned_and_health_tracks_io_failures(self) -> None:
        sensor = FakeAS5048A([10])
        encoder = AS5048AEncoder(
            sensor=sensor,
            monotonic_ns=lambda: 0,
        )
        encoder.initialize()
        sensor.read_diagnostics = lambda: (_ for _ in ()).throw(OSError("spi"))

        health = encoder.read_health()

        self.assertFalse(health.available)
        self.assertEqual(health.communication_errors, 1)
        encoder.close()
        self.assertFalse(sensor.closed)


if __name__ == "__main__":
    unittest.main()
