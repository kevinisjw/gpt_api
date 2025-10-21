import time
import asyncio
from functools import wraps
from typing import Any, Callable
from logger_setup import logger

def async_retry(max_attempts: int = 3, delay: float = 1.0):
    """异步重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败: {str(e)}")
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay * (attempt + 1))
            
            logger.error(f"函数 {func.__name__} 所有重试均失败")
            raise last_exception
        return wrapper
    return decorator

def format_timestamp() -> str:
    """格式化时间戳"""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def validate_prompt_length(prompt: str, max_length: int = 4000) -> bool:
    """验证提示词长度"""
    return len(prompt) <= max_length
