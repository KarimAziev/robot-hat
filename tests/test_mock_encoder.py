import unittest

from robot_hat.mock.encoder import MockEncoder


class TestMockEncoder(unittest.TestCase):
    def test_configurable_mock_counts_resets_and_reports_health(self) -> None:
        encoder = MockEncoder(
            initial_ticks=10,
            ticks_per_sample=-2,
            monotonic_ns=lambda: 42,
        )
        encoder.initialize()

        sample = encoder.read_sample()
        self.assertEqual(sample.ticks, 8)
        self.assertEqual(sample.timestamp_monotonic_ns, 42)
        encoder.reset(100)
        self.assertEqual(encoder.read_sample().ticks, 98)
        self.assertTrue(encoder.read_health().available)


if __name__ == "__main__":
    unittest.main()
