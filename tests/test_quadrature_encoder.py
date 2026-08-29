import unittest

from robot_hat import (
    EncoderABC,
    EncoderBackendError,
    EncoderClosedError,
    EncoderSample,
    MockQuadratureCounterBackend,
    QuadratureCounterBackendABC,
    QuadratureCounterSnapshot,
    QuadratureDecodeMode,
    QuadratureDecoder,
    QuadratureEncoder,
    as530x_counts_per_revolution,
)
from robot_hat.exceptions import EncoderNotInitializedError


class TestQuadratureEncoder(unittest.TestCase):
    def test_implements_encoder_contract_and_preserves_snapshot(self) -> None:
        backend = MockQuadratureCounterBackend(
            initial_count=-12,
            monotonic_ns=lambda: 99,
        )
        encoder = QuadratureEncoder(backend=backend)

        self.assertIsInstance(encoder, EncoderABC)
        encoder.initialize()
        sample = encoder.read_sample()

        self.assertIsInstance(sample, EncoderSample)
        self.assertEqual(sample.ticks, -12)
        self.assertEqual(sample.timestamp_monotonic_ns, 99)

    def test_positive_negative_counts_and_direction_inversion(self) -> None:
        backend = MockQuadratureCounterBackend()
        encoder = QuadratureEncoder(backend=backend, invert_direction=True)
        encoder.initialize()

        backend.advance(20)
        self.assertEqual(encoder.read_sample().ticks, -20)
        backend.advance(-50)
        self.assertEqual(encoder.read_sample().ticks, 30)

    def test_reset_uses_public_tick_direction(self) -> None:
        backend = MockQuadratureCounterBackend()
        encoder = QuadratureEncoder(backend=backend, invert_direction=True)
        encoder.initialize()

        encoder.reset(15)

        self.assertEqual(backend.read_snapshot().count, -15)
        self.assertEqual(encoder.read_sample().ticks, 15)

    def test_health_maps_generic_diagnostics_and_availability(self) -> None:
        backend = MockQuadratureCounterBackend()
        encoder = QuadratureEncoder(backend=backend)

        self.assertFalse(encoder.read_health().available)
        encoder.initialize()
        backend.inject_invalid_transitions(4)
        health = encoder.read_health()
        self.assertTrue(health.available)
        self.assertEqual(health.invalid_transitions, 4)
        self.assertEqual(health.communication_errors, 0)
        self.assertIsNone(health.magnet_detected)
        self.assertIsNone(health.magnet_too_weak)
        self.assertIsNone(health.magnet_too_strong)

    def test_backend_failures_are_counted_and_sample_errors_are_typed(self) -> None:
        backend = MockQuadratureCounterBackend()
        encoder = QuadratureEncoder(backend=backend)
        encoder.initialize()
        backend.set_read_error(OSError("injected"))

        with self.assertRaises(EncoderBackendError) as context:
            encoder.read_sample()
        self.assertIsInstance(context.exception.__cause__, OSError)
        backend.set_read_error(None)
        health = encoder.read_health()
        self.assertTrue(health.available)
        self.assertEqual(health.communication_errors, 1)

    def test_unavailable_backend_produces_unavailable_health(self) -> None:
        backend = MockQuadratureCounterBackend()
        encoder = QuadratureEncoder(backend=backend)
        encoder.initialize()

        backend.set_available(False)
        health = encoder.read_health()

        self.assertFalse(health.available)
        self.assertEqual(health.communication_errors, 1)

    def test_closed_encoder_is_unavailable_and_rejects_reads(self) -> None:
        encoder = QuadratureEncoder(backend=MockQuadratureCounterBackend())
        encoder.initialize()

        encoder.close()
        encoder.close()

        self.assertFalse(encoder.read_health().available)
        with self.assertRaises(EncoderClosedError):
            encoder.read_sample()

    def test_read_before_initialization_is_typed(self) -> None:
        encoder = QuadratureEncoder(backend=MockQuadratureCounterBackend())

        with self.assertRaises(EncoderNotInitializedError):
            encoder.read_sample()

    def test_default_ownership_closes_backend(self) -> None:
        backend = MockQuadratureCounterBackend()
        encoder = QuadratureEncoder(backend=backend)
        encoder.initialize()

        encoder.close()

        self.assertTrue(backend.closed)

    def test_shared_backend_is_not_closed(self) -> None:
        backend = MockQuadratureCounterBackend()
        encoder = QuadratureEncoder(backend=backend, owns_backend=False)
        encoder.initialize()

        encoder.close()

        self.assertFalse(backend.closed)
        self.assertEqual(backend.read_snapshot().count, 0)

    def test_left_and_right_encoders_have_independent_state(self) -> None:
        left_backend = MockQuadratureCounterBackend()
        right_backend = MockQuadratureCounterBackend()
        left = QuadratureEncoder(backend=left_backend)
        right = QuadratureEncoder(
            backend=right_backend,
            invert_direction=True,
        )
        left.initialize()
        right.initialize()

        left_backend.advance(100)
        right_backend.advance(-80)

        self.assertEqual(left.read_sample().ticks, 100)
        self.assertEqual(right.read_sample().ticks, 80)

    def test_public_exports_do_not_access_hardware(self) -> None:
        self.assertTrue(issubclass(QuadratureEncoder, EncoderABC))
        self.assertTrue(
            issubclass(MockQuadratureCounterBackend, QuadratureCounterBackendABC)
        )
        self.assertEqual(QuadratureDecodeMode.X4.value, 4)
        self.assertEqual(QuadratureCounterSnapshot(0, 0).count, 0)
        self.assertEqual(QuadratureDecoder().read_snapshot().count, 0)
        self.assertEqual(as530x_counts_per_revolution(12), 1920)


if __name__ == "__main__":
    unittest.main()
