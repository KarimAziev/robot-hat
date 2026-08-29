#!/usr/bin/env python3
"""Operator-assisted hardware-in-the-loop validation for motor backends."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from robot_hat import (
    GPIODCMotorConfig,
    I2CDCMotorConfig,
    MotorABC,
    MotorFactory,
    PWMDriverConfig,
    PhaseMotorConfig,
    SMBusManager,
    version,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run low-speed, operator-observed motor checks and write a JSON "
            "evidence report. Lift driven wheels clear of the work surface."
        )
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--rig-id", required=True)
    parser.add_argument("--speed", type=float, default=20.0)
    parser.add_argument("--duration", type=float, default=0.75)
    parser.add_argument(
        "--acknowledge-motion-risk",
        action="store_true",
        help="Confirm lifted wheels, a restrained rig, and a ready emergency stop.",
    )
    return parser.parse_args()


def _load_config(path: Path) -> tuple[MotorABC, Dict[str, Any], str]:
    raw = path.read_bytes()
    payload = json.loads(raw)
    motor_type = payload["motor_type"]
    values = dict(payload["config"])

    if motor_type == "i2c_dc":
        values["driver"] = PWMDriverConfig(**values["driver"])
        config = I2CDCMotorConfig(**values)
        bus = SMBusManager.get_bus(config.driver.bus)
        motor = MotorFactory.create_motor(config, bus=bus)
    elif motor_type == "gpio_dc":
        motor = MotorFactory.create_motor(GPIODCMotorConfig(**values))
    elif motor_type == "phase":
        motor = MotorFactory.create_motor(PhaseMotorConfig(**values))
    else:
        raise ValueError("motor_type must be i2c_dc, gpio_dc, or phase")

    return motor, payload, hashlib.sha256(raw).hexdigest()


def _confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def _git_revision() -> tuple[str | None, bool | None]:
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--short"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        return revision, dirty
    except (OSError, subprocess.CalledProcessError):
        return None, None


def _pulse(motor: MotorABC, speed: float, duration: float) -> None:
    motor.set_speed(speed)
    time.sleep(duration)
    motor.stop()


def main() -> int:
    args = _parse_args()
    if not args.acknowledge_motion_risk:
        raise SystemExit(
            "Refusing motion: pass --acknowledge-motion-risk after lifting wheels"
        )
    if not 0 < args.speed <= 30:
        raise SystemExit("HIL speed must be greater than 0 and no more than 30")
    if not 0 < args.duration <= 2:
        raise SystemExit(
            "HIL duration must be greater than 0 and no more than 2 seconds"
        )
    if args.output.exists():
        raise SystemExit(f"Refusing to overwrite existing evidence: {args.output}")
    if not _confirm(
        "Are driven wheels clear, the rig restrained, and emergency stop ready?"
    ):
        raise SystemExit("Safety confirmation declined")

    started_at = datetime.now(timezone.utc).isoformat()
    revision, dirty = _git_revision()
    checks: list[Dict[str, Any]] = []
    motor: MotorABC | None = None
    config_payload: Dict[str, Any] | None = None
    config_sha256: str | None = None
    error: str | None = None

    try:
        motor, config_payload, config_sha256 = _load_config(args.config)
        motor.stop()

        _pulse(motor, args.speed, args.duration)
        checks.append(
            {
                "name": "positive_command_direction",
                "passed": _confirm(
                    "Did the positive command rotate in the rig's expected direction?"
                ),
                "command": args.speed,
            }
        )

        original_direction = motor.direction
        inverted_direction = -original_direction
        motor.update_calibration_direction(inverted_direction)
        _pulse(motor, args.speed, args.duration)
        checks.append(
            {
                "name": "direction_calibration_inverts_output",
                "passed": _confirm(
                    "Did direction calibration reverse the observed rotation?"
                ),
                "command": args.speed,
                "calibration_direction": inverted_direction,
            }
        )
        motor.update_calibration_direction(original_direction)

        original_offset = motor.speed_offset
        motor.update_calibration_speed(20)
        motor.set_speed(0)
        time.sleep(args.duration)
        motor.stop()
        checks.append(
            {
                "name": "zero_command_remains_stopped_with_offset",
                "passed": _confirm(
                    "Did the motor remain fully stopped with a non-zero offset?"
                ),
                "command": 0,
                "speed_offset": 20,
            }
        )
        motor.update_calibration_speed(original_offset)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if motor is not None:
            try:
                motor.stop()
            except Exception as exc:
                if error is None:
                    error = f"cleanup {type(exc).__name__}: {exc}"
            try:
                motor.close()
            except Exception as exc:
                if error is None:
                    error = f"cleanup {type(exc).__name__}: {exc}"
        try:
            SMBusManager.close_all()
        except Exception as exc:
            if error is None:
                error = f"cleanup {type(exc).__name__}: {exc}"

    passed = error is None and bool(checks) and all(check["passed"] for check in checks)
    report = {
        "schema_version": 1,
        "result": "passed" if passed else "failed",
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "operator": args.operator,
        "rig_id": args.rig_id,
        "robot_hat_version": version,
        "git_revision": revision,
        "git_dirty": dirty,
        "python": sys.version,
        "platform": platform.platform(),
        "config_sha256": config_sha256,
        "config": config_payload,
        "checks": checks,
        "error": error,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2, sort_keys=True)
        output.write("\n")
    print(f"Wrote {report['result']} HIL report to {args.output}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
