import asyncio
import logging
from typing import Callable, TypeVar
T = TypeVar('T')
logger = logging.getLogger(__name__)
async def retry_async(
    func: Callable[..., T],
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> T:
    delay = initial_delay
    last_exception = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            if attempt == max_attempts:
                logger.error(
                    f"All {max_attempts} attempts failed. Last error: {e}",
                    exc_info=True
                )
                raise
            logger.warning(
                f"Attempt {attempt}/{max_attempts} failed: {e}. "
                f"Retrying in {delay}s..."
            )
            await asyncio.sleep(delay)
            delay *= backoff_factor
    raise last_exception
