# 2D lidar and UART support

`robot_hat` exposes a device-independent `Lidar2DABC` for planar range sensors and
ships an initial `RPLidarC1` implementation. The API deliberately separates three
layers:

1. `UARTABC` moves bytes and owns serial-port concerns.
2. A lidar driver implements a vendor protocol and converts its samples into
   `LidarMeasurement` values.
3. `Lidar2DABC.iter_scans()` groups start markers into complete revolutions for a
   mapping or SLAM frontend.

This keeps USB enumeration, UART behavior, Slamtec framing, and SLAM data handling
independently replaceable and testable.

## Installation

PySerial is a normal package dependency and works on Linux/aarch64, including a
Raspberry Pi 5:

```bash
pip install robot-hat
```

No Slamtec C++ SDK or ROS installation is required for Standard-mode scans. The
implementation follows the packet definitions in Slamtec's public SDK and uses
the C1 settings published in the official ROS launch file: 460800 baud, 8 data
bits, no parity, and one stop bit.

## RPLIDAR C1 quick start

Prefer the persistent `/dev/serial/by-id/...` name when Linux provides one. It is
stable when USB enumeration order changes, unlike `/dev/ttyUSB0`.

```python
from robot_hat import RPLidarC1, RPLidarC1Config

config = RPLidarC1Config(
    port="/dev/serial/by-id/usb-Silicon_Labs_CP2102N_...",
)
lidar = RPLidarC1(config)

with lidar:
    info = lidar.get_device_info()
    health = lidar.get_health()
    if not health.is_usable:
        raise RuntimeError(f"Lidar health error: {health.error_code}")

    lidar.start_scan()
    try:
        for scan in lidar.iter_scans(min_measurements=100):
            submit_to_slam(
                timestamp=scan.started_at,
                points_m=scan.xy_points_m,
            )
    finally:
        lidar.stop_scan()
```

Timestamps come from `time.monotonic()` and are therefore suitable for measuring
intervals and correlating scans with odometry captured from the same monotonic
clock. They are not wall-clock or ROS epoch timestamps.

Slamtec's wire angle uses a left-handed coordinate system and increases clockwise.
The generic API converts it to a right-handed sensor-local frame: zero remains the
sensor's forward x-axis and positive angles increase counter-clockwise. This avoids
silently mirroring maps in SLAM software that expects the conventional robotics
frame.

`iter_scans()` discards bytes before the first revolution marker and never emits a
trailing partial revolution. Zero-distance samples remain available in
`scan.measurements` with `is_valid == False`; `scan.valid_measurements` and
`scan.xy_points_m` omit them.

## Finding a USB-UART adapter

Ports can be listed or selected by USB metadata instead of guessing a tty number:

```python
from robot_hat import (
    RPLidarC1,
    RPLidarC1Config,
    USBUARTSelector,
    find_usb_uart_device,
    list_usb_uart_devices,
)

for device in list_usb_uart_devices():
    print(device.port, device.vendor_id, device.product_id, device.serial_number)

device = find_usb_uart_device(
    USBUARTSelector(
        vendor_id=0x10C4,       # Example only: inspect your adapter.
        product_id=0xEA60,
        serial_number="...",   # Best discriminator when several are attached.
    )
)
lidar = RPLidarC1(RPLidarC1Config(port=device.port))
```

An empty selector may be useful for diagnostics but raises
`UARTPortAmbiguousError` when several ports exist. A selector with no match raises
`UARTPortNotFoundError`.

## Raspberry Pi 5 native UART

The C1 UART uses 3.3 V TTL logic. It is not an RS-232 voltage-level interface.
For a bare sensor connection:

- connect sensor TX to the Pi RX signal;
- connect sensor RX to the Pi TX signal;
- connect signal grounds;
- power the bare C1 from a regulated 5 V supply capable of its approximately
  800 mA startup demand (the datasheet specifies 4.8–5.2 V);
- never power the motor or lidar through a GPIO signal pin.

Use Raspberry Pi configuration tools to enable a hardware serial port and disable
the Linux serial console on that port. Use `/dev/serial0` in the application so
the board-specific primary-UART mapping remains an operating-system concern:

```python
lidar = RPLidarC1(RPLidarC1Config(port="/dev/serial0"))
```

The user running the process must have read/write permission for the tty. On
Raspberry Pi OS this normally means membership in the `dialout` group followed by
a new login. A targeted udev rule is safer than running the application with
`sudo` or making every tty world-writable.

At 460800 baud, use a hardware UART and short, correctly grounded wiring. Avoid a
software UART. A USB adapter must support 460800 baud and 3.3 V TTL levels.

## Injecting a UART or using the mock

Injecting the byte transport makes application and protocol tests independent of
real hardware:

```python
from robot_hat import MockUART, RPLidarC1, RPLidarC1Config

config = RPLidarC1Config(reset_wait_s=0, stop_wait_s=0)
uart = MockUART(config=config.uart_config)
lidar = RPLidarC1(config, uart=uart)
```

An injected UART belongs to the caller. `RPLidarC1.disconnect()` stops an active
scan but does not close that UART. A `SerialUART` created internally by
`RPLidarC1` is closed automatically.

## Lifecycle and error handling

Device-info and health requests are allowed only while no scan stream is active.
A typical lifecycle is:

```text
connect -> device info / health -> start scan -> consume -> stop scan -> disconnect
```

Protocol failures use specific exception types:

- `LidarConnectionError`: an operation requires an open transport;
- `LidarStateError`: a query conflicts with an active scan, or scanning has not
  started;
- `LidarTimeoutError`: the UART timeout elapsed before a complete frame arrived;
- `LidarProtocolError`: a descriptor, packet type, packet length, or measurement
  frame is invalid.

The Standard measurement parser validates the complementary scan marker and angle
check bit. It uses a bounded sliding window to recover when a byte is dropped or
startup begins in the middle of a packet.

## Adding another 2D lidar

Implement `Lidar2DABC` and keep vendor details inside the concrete driver. In
particular:

- report angles in degrees in `[0, 360)` and distances in metres;
- define the sensor-local angle direction clearly (the common API is
  counter-clockwise);
- timestamp samples from a monotonic clock as close to receipt as practical;
- preserve invalid samples with a zero distance when that reflects the wire data;
- set `start_of_scan` on the first point of each revolution;
- inject transport interfaces instead of opening hardware during import;
- close only resources created by the driver;
- test framing, conversions, timeouts, resynchronization, and scan boundaries with
  fake bytes.

Future Slamtec work can add Express/HQ capsule decoding behind the same
`Lidar2DABC`; SLAM consumers do not need to change when the wire format changes.

## Current scope

The initial C1 driver implements the official **Standard** scan stream plus device
information, health, reset, start, and stop commands. It does not yet implement
Express/HQ capsule modes, scan-mode enumeration, or motor speed tuning. The C1 has
closed-loop motor control and its running state follows the laser scan command, so
an extra DTR/PWM motor-start action is intentionally not sent for this model.

References:

- [Slamtec RPLIDAR SDK](https://github.com/Slamtec/rplidar_sdk)
- [Slamtec RPLIDAR ROS C1 launch configuration](https://github.com/Slamtec/rplidar_ros/blob/master/launch/rplidar_c1.launch)
- [Slamtec C1 product specifications](https://www.slamtec.com/en/c1/spec)
