import unittest
from unittest.mock import patch

from robot_hat.drivers.angle.as5600l import AS5600LStatus
from robot_hat.exceptions import EncoderMagnetError, EncoderNotInitializedError
from robot_hat.sensors.encoder.as5600l_encoder import (
    AS5600LEncoder,
    DEFAULT_MAX_SAMPLE_GAP_NS,
)


GOOD_STATUS = AS5600LStatus(True, False, False, 0x20)


class FakeAS5600L:
    def __init__(
        self,
        raw_angles: list[int],
        *,
        status: AS5600LStatus = GOOD_STATUS,
    ) -> None:
        self.raw_angles = iter(raw_angles)
        self.status = status
        self.closed = False

    def read_status(self) -> AS5600LStatus:
        return self.status

    def read_raw_angle(self) -> int:
        return next(self.raw_angles)

    def close(self) -> None:
        self.closed = True


class TestAS5600LEncoder(unittest.TestCase):
    def _encoder(
        self,
        sensor: FakeAS5600L,
        timestamps: list[int],
        *,
        invert_direction: bool = False,
        max_sample_gap_ns: int | None = DEFAULT_MAX_SAMPLE_GAP_NS,
    ) -> AS5600LEncoder:
        with patch(
            "robot_hat.sensors.encoder.as5600l_encoder.AS5600L",
            return_value=sensor,
        ):
            return AS5600LEncoder(
                monotonic_ns=iter(timestamps).__next__,
                invert_direction=invert_direction,
                max_sample_gap_ns=max_sample_gap_ns,
            )

    def test_requires_initialize_and_unwraps_both_boundary_directions(self) -> None:
        encoder = self._encoder(FakeAS5600L([4090, 3, 4094]), [0, 10, 20])
        with self.assertRaises(EncoderNotInitializedError):
            encoder.read_sample()

        encoder.initialize()

        self.assertEqual(encoder.read_sample().ticks, 9)
        final = encoder.read_sample()
        self.assertEqual(final.ticks, 4)
        self.assertEqual(final.timestamp_monotonic_ns, 20)

    def test_inverts_direction_and_atomically_resets_counter(self) -> None:
        encoder = self._encoder(
            FakeAS5600L([100, 110, 115]),
            [0, 10, 20],
            invert_direction=True,
        )
        encoder.initialize()

        self.assertEqual(encoder.read_sample().ticks, -10)
        encoder.reset(50)
        self.assertEqual(encoder.read_sample().ticks, 45)

    def test_long_gap_rebaselines_without_inventing_motion(self) -> None:
        encoder = self._encoder(
            FakeAS5600L([100, 900, 905]),
            [0, 101, 110],
            max_sample_gap_ns=100,
        )
        encoder.initialize()

        with self.assertLogs(
            "robot_hat.sensors.encoder.as5600l_encoder", level="WARNING"
        ):
            self.assertEqual(encoder.read_sample().ticks, 0)
        self.assertEqual(encoder.read_sample().ticks, 5)
        self.assertEqual(encoder.read_health().invalid_transitions, 1)

    def test_half_turn_is_invalid_and_does_not_change_ticks(self) -> None:
        encoder = self._encoder(FakeAS5600L([0, 2048]), [0, 10])
        encoder.initialize()

        with self.assertLogs(
            "robot_hat.sensors.encoder.as5600l_encoder", level="WARNING"
        ):
            self.assertEqual(encoder.read_sample().ticks, 0)
        self.assertEqual(encoder.read_health().invalid_transitions, 1)

    def test_rejects_missing_weak_and_strong_magnets(self) -> None:
        bad_statuses = [
            AS5600LStatus(False, False, False, 0),
            AS5600LStatus(True, True, False, 0x30),
            AS5600LStatus(True, False, True, 0x28),
        ]
        for status in bad_statuses:
            with self.subTest(status=status):
                encoder = self._encoder(FakeAS5600L([10], status=status), [0])
                with self.assertRaises(EncoderMagnetError):
                    encoder.initialize()
                self.assertEqual(encoder.read_health().communication_errors, 0)

    def test_live_magnet_fault_rejects_sample_and_rebaselines(self) -> None:
        sensor = FakeAS5600L([100, 120, 125])
        encoder = self._encoder(sensor, [0, 10, 20])
        encoder.initialize()
        sensor.status = AS5600LStatus(True, True, False, 0x30)

        with self.assertRaises(EncoderMagnetError):
            encoder.read_sample()
        sensor.status = GOOD_STATUS

        self.assertEqual(encoder.read_sample().ticks, 0)
        self.assertEqual(encoder.read_sample().ticks, 5)
        self.assertEqual(encoder.read_health().invalid_transitions, 1)

    def test_health_tracks_communication_errors_and_close(self) -> None:
        sensor = FakeAS5600L([10])
        encoder = self._encoder(sensor, [0])
        encoder.initialize()
        sensor.status = GOOD_STATUS
        sensor.read_status = lambda: (_ for _ in ()).throw(OSError("i2c"))

        health = encoder.read_health()

        self.assertFalse(health.available)
        self.assertEqual(health.communication_errors, 1)
        encoder.close()
        self.assertTrue(sensor.closed)
        self.assertFalse(encoder.read_health().available)


if __name__ == "__main__":
    unittest.main()
