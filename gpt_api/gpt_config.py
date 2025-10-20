import os
from pathlib import Path
from dotenv import load_dotenv
from logger_setup import LOG_FILE_PATH

load_dotenv()


class Config:
    def __init__(self) -> None:
        # OpenRouter 配置
        self.OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
        self.OPENROUTER_BASE_URL = os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        )
        self.OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "https://localhost")
        self.OPENROUTER_APP_TITLE = os.getenv("OPENROUTER_APP_TITLE", "AI API Service")

        # 服务配置
        self.API_HOST = os.getenv("GPT_API_HOST", "0.0.0.0")
        self.API_PORT = int(os.getenv("GPT_API_PORT", 8000))

        # 文本模型配置
        self.DEFAULT_TEXT_MODEL  = "deepseek/deepseek-chat-v3-0324:free"
        self.ADVANCED_TEXT_MODEL = "deepseek/deepseek-chat-v3.1"
        # self.DEFAULT_TEXT_MODEL = "qwen/qwen3-max"
        self.MAX_PROMPT_TOKENS = 4096 # max(text_tokens) <= 4096
        self.MAX_OUTPUT_TOKENS = 1024*30 # max(text_tokens) <= 4096


        self.OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        ## 图像模型
        self.DEFAULT_IMAGE_MODEL = "qwen/qwen3-vl-235b-a22b-instruct"
        self.ADVANCED_IMAGE_MODEL = "qwen/qwen3-vl-235b-a22b-instruct"
        self.MAX_IMAGE_SIZE = 640 # max(image_width, image_height)<=640
        self.MIN_IMAGE_SIZE = 240 # min(image_width, image_height)>=240

        # 请求限制
        self.MAX_REQUEST_SIZE = 1024 * 1024 * 10  # 10MB
        self.REQUEST_TIMEOUT = 180.0
        self.HEALTH_CHECK_INTERVAL = float(os.getenv("HEALTH_CHECK_INTERVAL", 60))
        self.MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", 1024 * 30))
        self.TEMPERATURE = float(os.getenv("TEMPERATURE", 0.0))
        self.IS_STREAM = bool(os.getenv("IS_STREAM", False))
        
        # 日志配置
        log_env = os.getenv("LOG_PATH")
        log_path = Path(log_env) if log_env else LOG_FILE_PATH
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.LOG_PATH = log_path


gpt_general_config = Config()
