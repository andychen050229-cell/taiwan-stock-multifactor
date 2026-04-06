"""
日誌管理模組 — 基於 loguru 的三層日誌系統

三層設計：
  - Console: 即時輸出，開發用（DEBUG/INFO）
  - File (app.log): 完整應用日誌（INFO+），自動輪替 10MB
  - File (error.log): 僅記錄錯誤（ERROR+），方便事後排查
"""
import sys
from pathlib import Path
from loguru import logger

_initialized = False


def get_logger(module_name: str = None, config: dict = None):
    """
    取得設定好的 logger 實例。

    Args:
        module_name: 模組名稱，會顯示在日誌中
        config: 設定字典（來自 YAML），可選

    Returns:
        loguru.logger 實例
    """
    global _initialized

    if not _initialized:
        _setup_logger(config)
        _initialized = True

    if module_name:
        return logger.bind(module=module_name)
    return logger


def _setup_logger(config: dict = None):
    """初始化三層日誌"""
    # 預設值
    log_dir = Path(config.get("paths", {}).get("logs", "logs")) if config else Path("logs")
    level = config.get("logging", {}).get("level", "INFO") if config else "INFO"
    fmt = (
        config.get("logging", {}).get("format", None) if config else None
    ) or "{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {module}:{function}:{line} | {message}"
    rotation = config.get("logging", {}).get("rotation", "10 MB") if config else "10 MB"
    retention = config.get("logging", {}).get("retention", "30 days") if config else "30 days"

    log_dir.mkdir(parents=True, exist_ok=True)

    # 清除預設 handler
    logger.remove()

    # Layer 1: Console — 即時輸出
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{module}</cyan>:<cyan>{function}</cyan> | {message}",
        colorize=True,
    )

    # Layer 2: app.log — 完整日誌
    logger.add(
        log_dir / "app.log",
        level="INFO",
        format=fmt,
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
    )

    # Layer 3: error.log — 僅錯誤
    logger.add(
        log_dir / "error.log",
        level="ERROR",
        format=fmt,
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
    )

    logger.info("Logger initialized | level={} | log_dir={}", level, log_dir)
