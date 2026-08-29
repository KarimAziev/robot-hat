import unittest

from robot_hat.data_types.quadrature import (
    QuadratureCounterSnapshot,
    QuadratureDecodeMode,
    as530x_counts_per_revolution,
)
from robot_hat.sensors.encoder.quadrature_decoder import QuadratureDecoder


FORWARD_CYCLE = ((False, False), (False, True), (True, True), (True, False))
REVERSE_CYCLE = ((False, False), (True, False), (True, True), (False, True))


def apply_cycles(
    decoder: QuadratureDecoder,
    states: tuple[tuple[bool, bool], ...],
    cycles: int = 1,
) -> None:
    decoder.update(*states[0])
    for _ in range(cycles):
        for state in (*states[1:], states[0]):
            decoder.update(*state)


class TestQuadratureDataTypes(unittest.TestCase):
    def test_snapshot_validates_monotonic_time_and_diagnostics(self) -> None:
        snapshot = QuadratureCounterSnapshot(-2, 42, 3)

        self.assertEqual(snapshot.count, -2)
        with self.assertRaises(ValueError):
            QuadratureCounterSnapshot(0, -1)
        with self.assertRaises(ValueError):
            QuadratureCounterSnapshot(0, 0, -1)

    def test_as530x_resolution_helper_distinguishes_decode_modes(self) -> None:
        self.assertEqual(as530x_counts_per_revolution(12), 1920)
        self.assertEqual(as530x_counts_per_revolution(16), 2560)
        self.assertEqual(as530x_counts_per_revolution(22), 3520)
        self.assertEqual(as530x_counts_per_revolution(12, QuadratureDecodeMode.X1), 480)
        self.assertEqual(as530x_counts_per_revolution(12, QuadratureDecodeMode.X2), 960)

    def test_as530x_resolution_helper_validates_arguments(self) -> None:
        with self.assertRaises(TypeError):
            as530x_counts_per_revolution(True)
        with self.assertRaises(ValueError):
            as530x_counts_per_revolution(0)


class TestQuadratureDecoder(unittest.TestCase):
    def test_complete_forward_x4_sequence(self) -> None:
        decoder = QuadratureDecoder(monotonic_ns=lambda: 100)

        apply_cycles(decoder, FORWARD_CYCLE)

        self.assertEqual(decoder.read_snapshot(), QuadratureCounterSnapshot(4, 100))

    def test_complete_reverse_x4_sequence(self) -> None:
        decoder = QuadratureDecoder()

        apply_cycles(decoder, REVERSE_CYCLE)

        self.assertEqual(decoder.read_snapshot().count, -4)

    def test_multiple_complete_sequences_accumulate(self) -> None:
        decoder = QuadratureDecoder()

        apply_cycles(decoder, FORWARD_CYCLE, cycles=5)
        apply_cycles(decoder, REVERSE_CYCLE, cycles=2)

        self.assertEqual(decoder.read_snapshot().count, 12)

    def test_x1_x2_and_x4_semantics(self) -> None:
        for mode in QuadratureDecodeMode:
            with self.subTest(mode=mode):
                forward = QuadratureDecoder(decode_mode=mode)
                reverse = QuadratureDecoder(decode_mode=mode)
                apply_cycles(forward, FORWARD_CYCLE)
                apply_cycles(reverse, REVERSE_CYCLE)
                self.assertEqual(forward.read_snapshot().count, mode.value)
                self.assertEqual(reverse.read_snapshot().count, -mode.value)

    def test_repeated_state_is_not_movement_or_error(self) -> None:
        decoder = QuadratureDecoder()

        decoder.update(False, False)
        decoder.update(False, False)
        decoder.update(False, False)

        self.assertEqual(decoder.read_snapshot().count, 0)
        self.assertEqual(decoder.read_snapshot().invalid_transitions, 0)

    def test_every_directed_two_bit_transition_is_invalid(self) -> None:
        invalid_pairs = (
            ((False, False), (True, True)),
            ((True, True), (False, False)),
            ((False, True), (True, False)),
            ((True, False), (False, True)),
        )
        for initial, changed in invalid_pairs:
            with self.subTest(initial=initial, changed=changed):
                decoder = QuadratureDecoder()
                decoder.update(*initial)
                decoder.update(*changed)
                snapshot = decoder.read_snapshot()
                self.assertEqual(snapshot.count, 0)
                self.assertEqual(snapshot.invalid_transitions, 1)

    def test_invalid_transition_counter_accumulates(self) -> None:
        decoder = QuadratureDecoder()

        decoder.update(False, False)
        decoder.update(True, True)
        decoder.update(False, False)

        self.assertEqual(decoder.read_snapshot().invalid_transitions, 2)

    def test_initial_state_establishes_phase_without_false_count(self) -> None:
        decoder = QuadratureDecoder()

        decoder.update(True, True)

        self.assertEqual(decoder.read_snapshot().count, 0)

    def test_reverse_movement_cancels_partial_forward_movement(self) -> None:
        decoder = QuadratureDecoder(decode_mode=QuadratureDecodeMode.X1)

        decoder.update(False, False)
        decoder.update(False, True)
        decoder.update(True, True)
        decoder.update(False, True)
        decoder.update(False, False)

        self.assertEqual(decoder.read_snapshot().count, 0)

    def test_reset_preserves_phase_without_promoting_partial_movement(self) -> None:
        decoder = QuadratureDecoder(decode_mode=QuadratureDecodeMode.X1)
        decoder.update(False, False)
        decoder.update(False, True)
        decoder.reset(10)

        decoder.update(True, True)
        self.assertEqual(decoder.read_snapshot().count, 10)
        decoder.update(True, False)
        decoder.update(False, False)
        decoder.update(False, True)
        self.assertEqual(decoder.read_snapshot().count, 11)


if __name__ == "__main__":
    unittest.main()
