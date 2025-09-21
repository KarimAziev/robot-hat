import unittest
from types import SimpleNamespace
from typing import Dict, Optional, Union, cast

import robot_hat.sensors.ultrasonic.HC_SR04 as hc_mod
from robot_hat.exceptions import UltrasonicEchoPinError
from robot_hat.pin import Pin, PinModeType, PinPullType


class FakeTime:

    def __init__(self, start: float = 0.0, small_step: float = 1e-6):
        self.current = float(start)
        self.small_step = float(small_step)

    def time(self) -> float:
        self.current += self.small_step
        return self.current

    def sleep(self, dt) -> None:
        self.current += float(dt)


class FakePin:
    OUT = 0x01
    IN = 0x02
    PULL_UP = 0x11
    PULL_DOWN = 0x12
    PULL_NONE = None

    _echo_behaviors = {}
    _initial_high = {}
    _force_no_gpio = False
    _last_trigger_time = {}
    _fake_time: Optional[FakeTime] = None

    def __init__(
        self,
        pin: Union[int, str],
        mode: Optional[PinModeType] = None,
        pull: Optional[PinPullType] = None,
        pin_dict: Dict[str, int] = Pin.DEFAULT_PIN_MAPPING.copy(),
    ) -> None:
        self._pin_num = pin
        self._board_name = f"GPIO{pin}"
        self._mode = mode
        self._pull = pull
        self.dict = pin_dict
        if mode in [None, self.OUT]:

            class OutGPIO:
                def __init__(self, parent):
                    self._pin = parent._pin_num
                    self.parent = parent

                def on(self):
                    FakePin._last_trigger_time[self._pin] = cast(
                        FakeTime, FakePin._fake_time
                    ).time()

                def off(self):
                    pass

                @property
                def value(self):
                    return 0

                def close(self):
                    pass

            self.gpio = OutGPIO(self)
        else:
            if FakePin._force_no_gpio:
                self.gpio = None
            else:

                class InGPIO:
                    def __init__(self, parent):
                        self._pin = parent._pin_num
                        self._created_at = cast(FakeTime, FakePin._fake_time).time()
                        self.parent = parent

                    @property
                    def value(self):
                        now = cast(FakeTime, FakePin._fake_time).time()
                        if FakePin._last_trigger_time:
                            latest_trigger = max(FakePin._last_trigger_time.values())
                        else:
                            latest_trigger = None

                        if latest_trigger is not None:
                            beh = FakePin._echo_behaviors.get(self._pin)
                            if beh is None:
                                return 0
                            start_offset, duration = beh
                            dt = now - latest_trigger
                            if start_offset <= dt < start_offset + duration:
                                return 1
                            else:
                                return 0
                        else:
                            init_dur = FakePin._initial_high.get(self._pin)
                            if init_dur:
                                if (now - self._created_at) < init_dur:
                                    return 1
                                else:
                                    return 0
                            return 0

                    def close(self):
                        pass

                self.gpio = InGPIO(self)

    def close(self):
        if self.gpio is not None:
            try:
                self.gpio.close()
            except Exception:
                pass

    def setup(self, mode, pull=None):
        self._mode = mode
        self._pull = pull

    def on(self):
        if hasattr(self.gpio, "on"):
            self.gpio.on()  # type: ignore
        else:
            FakePin._last_trigger_time[self._pin_num] = FakePin._fake_time.time()  # type: ignore
        return 1

    def off(self):
        if hasattr(self.gpio, "off"):
            self.gpio.off()  # type: ignore
        return 0

    def value(self, value=None):
        if value is None:
            return self.gpio.value if self.gpio is not None else None
        return 1 if value else 0

    def high(self):
        return self.on()

    def low(self):
        return self.off()


class TestHCSR04(unittest.TestCase):
    def setUp(self):
        self._orig_Pin = hc_mod.Pin
        self._orig_time = hc_mod.time

        self.fake_time = FakeTime(start=0.0, small_step=1e-6)
        FakePin._fake_time = self.fake_time  # type: ignore

        hc_mod.Pin = FakePin
        hc_mod.time = SimpleNamespace(
            time=self.fake_time.time, sleep=self.fake_time.sleep
        )

    def tearDown(self):
        hc_mod.Pin = self._orig_Pin
        hc_mod.time = self._orig_time
        FakePin._echo_behaviors.clear()
        FakePin._initial_high.clear()
        FakePin._force_no_gpio = False
        FakePin._last_trigger_time.clear()
        FakePin._fake_time = None

    def test_echo_pin_not_initialized_raises(self):
        FakePin._force_no_gpio = True

        trig_init = SimpleNamespace(_pin_num=11, close=lambda: None)
        echo_init = SimpleNamespace(_pin_num=12, close=lambda: None)

        us = hc_mod.Ultrasonic(cast(Pin, trig_init), cast(Pin, echo_init), timeout=0.05)

        with self.assertRaises(UltrasonicEchoPinError):
            us._read()

    def test_timeout_returns_minus_one(self):
        FakePin._echo_behaviors.clear()
        trig_init = SimpleNamespace(_pin_num=21, close=lambda: None)
        echo_init = SimpleNamespace(_pin_num=22, close=lambda: None)

        us = hc_mod.Ultrasonic(cast(Pin, trig_init), cast(Pin, echo_init), timeout=0.01)
        res = us._read()
        self.assertEqual(res, -1)

    def test_measurement_failure_returns_minus_two(self):
        echo_pin = 33
        trig_pin = 32
        FakePin._echo_behaviors[echo_pin] = (
            0.0,
            0.002,
        )

        trig_init = SimpleNamespace(_pin_num=trig_pin, close=lambda: None)
        echo_init = SimpleNamespace(_pin_num=echo_pin, close=lambda: None)

        us = hc_mod.Ultrasonic(cast(Pin, trig_init), cast(Pin, echo_init), timeout=0.1)
        res = us._read()
        self.assertEqual(res, -2)

    def test_normal_measurement_calculation(self):
        echo_pin = 45
        trig_pin = 44
        duration = 0.010
        start_offset = 0.0005
        FakePin._echo_behaviors[echo_pin] = (start_offset, duration)

        trig_init = SimpleNamespace(_pin_num=trig_pin, close=lambda: None)
        echo_init = SimpleNamespace(_pin_num=echo_pin, close=lambda: None)

        us = hc_mod.Ultrasonic(cast(Pin, trig_init), cast(Pin, echo_init), timeout=0.1)
        cm = us._read()

        expected = round(duration * hc_mod.Ultrasonic.SOUND_SPEED / 2 * 100, 2)
        self.assertAlmostEqual(cm, expected, delta=0.05)

    def test_read_tries_multiple_times(self):
        trig_init = SimpleNamespace(_pin_num=2, close=lambda: None)
        echo_init = SimpleNamespace(_pin_num=3, close=lambda: None)

        us = hc_mod.Ultrasonic(cast(Pin, trig_init), cast(Pin, echo_init), timeout=0.05)

        seq = [-1, -1, 42.5]
        calls = {"i": 0}

        def fake_read():
            i = calls["i"]
            calls["i"] += 1
            return seq[i] if i < len(seq) else seq[-1]

        us._read = fake_read
        res = us.read(times=5)
        self.assertEqual(res, 42.5)


if __name__ == "__main__":
    unittest.main()
