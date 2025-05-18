from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

# Number of retry attempts for I2C communication
RETRY_ATTEMPTS = 5

# Initial wait time (in seconds) before retry
INITIAL_WAIT = 0.01  # 10ms

# Maximum wait time (in seconds) for retry
MAX_WAIT = 0.2  # 200ms

# Random jitter (in seconds) to add randomness to retry timing
JITTER = 0.05  # 50ms

RETRY_DECORATOR = retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential_jitter(initial=INITIAL_WAIT, max=MAX_WAIT, jitter=JITTER),
    retry=retry_if_exception_type((OSError, TimeoutError)),
    reraise=True,
)
