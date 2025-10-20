import os
from pathlib import Path
from dotenv import load_dotenv
from gpt_api.logger_setup import LOG_FILE_PATH

load_dotenv()


class BaziConfig:
    def __init__(self) -> None:
        # 高德地图配置
        self.GAODE_API_KEY = os.getenv("GAODE_API_KEY", "2cd4e12a0bc627d900242b0ea6e10c65")
        
        # 服务配置
        self.API_HOST = os.getenv("BAZI_API_HOST", "0.0.0.0")
        self.API_PORT = int(os.getenv("BAZI_API_PORT", 8100))

        # 请求限制
        self.MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", 1024 * 1024))  # 1MB
        self.REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", 60))
        self.HEALTH_CHECK_INTERVAL = float(os.getenv("HEALTH_CHECK_INTERVAL", 60))
        
        # 日志配置
        log_env = os.getenv("BAZI_LOG_PATH")
        log_path = Path(log_env) if log_env else LOG_FILE_PATH
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.LOG_PATH = log_path


bazi_config = BaziConfig()
