import logging
import os
from pathlib import Path
from loguru import logger as _logger

LOG_FILE_PATH = Path(os.getenv("GLOBAL_LOG_PATH", "logs/gpt_service.log"))
LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

if not getattr(_logger, "_custom_configured", False):
    _logger.remove()
    _logger.configure(extra={"task_id": "-", "call_time": "-"})
    _logger.add(
        str(LOG_FILE_PATH),
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | task_id={extra[task_id]} | call_time={extra[call_time]} | {message}",
    )

    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level = _logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            frame, depth = logging.currentframe(), 2
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            _logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    _logger._custom_configured = True

logger = _logger

__all__ = ["logger", "LOG_FILE_PATH"]
