import time
from typing import Tuple, Union


def get_firmware_version() -> str:
    from robot_hat.i2c.i2c_manager import I2C

    ADDR = [0x14, 0x15]
    VERSSION_REG_ADDR = 0x05
    i2c = I2C(ADDR)
    version = i2c.mem_read(3, VERSSION_REG_ADDR)
    return f"{version[0]}.{version[1]}.{version[2]}"


def reset_mcu_sync(pin: Union[int, str] = 5) -> None:
    """
    Resets the MCU (Microcontroller Unit) by toggling the state of the MCU reset pin.

    This function uses the robot hat adapter's Pin interface to manipulate the "MCURST"
    pin. The reset process is handled by briefly pulling the reset pin low (off),
    waiting for 10 milliseconds, and then pulling it high (on) again, followed by
    another short delay. Finally, the pin resource is released or closed.

    Steps:
      1. Instantiate the `MCURST` Pin object.
      2. Set the pin to the OFF state (low) to reset the MCU.
      3. Wait for 10 milliseconds.
      4. Set the pin to the ON state (high) to complete the reset.
      5. Wait for another 10 milliseconds.
      6. Close the Pin instance to release resources.

    This function is synchronous and blocks execution while the delays occur.

    Example:
      reset_mcu_sync()
    """
    from robot_hat.pin import Pin

    mcu_reset = Pin(pin)
    mcu_reset.off()
    time.sleep(0.01)
    mcu_reset.on()
    time.sleep(0.01)
    mcu_reset.close()


def run_command(cmd: str) -> Tuple[Union[int, None], str]:
    """
    Run command and return status and output

    :param cmd: command to run
    :type cmd: str
    :return: status, output
    :rtype: tuple
    """
    import subprocess

    p = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )

    result = p.stdout.read().decode("utf-8") if p.stdout is not None else ""
    status = p.poll()
    return status, result
