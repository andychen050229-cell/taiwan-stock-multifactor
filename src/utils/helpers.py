"""
通用輔助函式
"""
import time
import functools
from pathlib import Path

from loguru import logger


def retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Retry 裝飾器 — 自動重試失敗的函式。

    Args:
        max_retries: 最大重試次數
        delay: 初始等待秒數
        backoff: 等待時間倍增因子

    Usage:
        @retry(max_retries=3)
        def unstable_function():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} failed after {max_retries} retries: {e}")
                        raise
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator


def ensure_dir(path: str | Path) -> Path:
    """確保目錄存在，不存在則建立"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def timer(func):
    """計時裝飾器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"{func.__name__} completed in {elapsed:.2f}s")
        return result
    return wrapper
