import unittest

from robot_hat import AS5048A, AS5048AProtocolError, MockAS5048ASPI, MockSPI


class TestMockSPI(unittest.TestCase):
    def test_records_transfers_and_returns_queued_then_zero_responses(self) -> None:
        spi = MockSPI([[0x12, 0x34]])

        self.assertEqual(spi.transfer([0xAA, 0x55]), [0x12, 0x34])
        self.assertEqual(spi.transfer([0x01]), [0x00])
        self.assertEqual(spi.transfers, ((0xAA, 0x55), (0x01,)))

    def test_close_is_idempotent_and_prevents_more_work(self) -> None:
        spi = MockSPI()
        spi.close()
        spi.close()

        self.assertTrue(spi.closed)
        with self.assertRaises(RuntimeError):
            spi.transfer([0])
        with self.assertRaises(RuntimeError):
            spi.queue_response([0])


class TestMockAS5048ASPI(unittest.TestCase):
    def test_emulates_pipelined_angle_diagnostics_and_magnitude(self) -> None:
        spi = MockAS5048ASPI(
            angle_counts=100,
            counts_per_angle_read=5,
            magnitude=0x2345,
            automatic_gain_control=37,
        )
        sensor = AS5048A(spi=spi)

        self.assertEqual(sensor.read_raw_angle(), 100)
        self.assertEqual(sensor.read_raw_angle(), 105)
        self.assertEqual(sensor.read_magnitude(), 0x2345)
        diagnostics = sensor.read_diagnostics()
        self.assertTrue(diagnostics.data_valid)
        self.assertEqual(diagnostics.automatic_gain_control, 37)
        self.assertEqual(spi.transfers[:2], ((0xFF, 0xFF), (0x00, 0x00)))

    def test_reports_and_clears_invalid_commands(self) -> None:
        sensor = AS5048A(spi=MockAS5048ASPI())

        with self.assertRaises(AS5048AProtocolError) as context:
            sensor.read_register(0x1234)

        self.assertTrue(context.exception.flags.invalid_command)
        self.assertFalse(context.exception.flags.framing_error)
        self.assertFalse(context.exception.flags.parity_error)
        self.assertEqual(sensor.clear_error_flags().raw, 0)

    def test_configuration_can_change_without_hardware(self) -> None:
        spi = MockAS5048ASPI()
        sensor = AS5048A(spi=spi)

        spi.set_angle_counts(16_383)
        spi.advance(2)
        spi.set_magnitude(123)
        spi.set_diagnostics(magnet_too_weak=True)

        self.assertEqual(sensor.read_raw_angle(), 1)
        self.assertEqual(sensor.read_magnitude(), 123)
        self.assertTrue(sensor.read_diagnostics().magnet_too_weak)

    def test_close_is_idempotent(self) -> None:
        spi = MockAS5048ASPI()
        spi.close()
        spi.close()

        self.assertTrue(spi.closed)
        with self.assertRaises(RuntimeError):
            spi.transfer([0, 0])


if __name__ == "__main__":
    unittest.main()
