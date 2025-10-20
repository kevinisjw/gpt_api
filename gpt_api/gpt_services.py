import time
from pathlib import Path
from typing import AsyncGenerator, Dict, Union
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from openai import OpenAI, AsyncOpenAI

from logger_setup import logger

from gpt_config import gpt_general_config
from gpt_models import GenerationRequest, GenerationResponse, HealthResponse
from task_prompt.fortune_prompt import FortuneCallBodyBuilder
from task_prompt.face_prompt import FaceCallBodyBuilder


BASE_DIR = Path(__file__).resolve().parent.parent
FACE_PAGE_PATH = BASE_DIR / "face_teller.html"
FORTUNE_PAGE_PATH = BASE_DIR / "fortune_teller.html"


class OpenRouterService:
    def __init__(self):
        """初始化 OpenRouter 服务"""
        self.config = gpt_general_config
        
        # 初始化同步客户端
        self.client = OpenAI(
            api_key=self.config.OPENROUTER_API_KEY,
            base_url=self.config.OPENROUTER_BASE_URL,
        )
        
        # 初始化异步客户端
        self.async_client = AsyncOpenAI(
            api_key=self.config.OPENROUTER_API_KEY,
            base_url=self.config.OPENROUTER_BASE_URL,
        )
        
        # 初始化 FortuneCallBodyBuilder
        self.fortune_builder = FortuneCallBodyBuilder()
        self.face_builder = FaceCallBodyBuilder()
        logger.info(f"OpenRouterService initialized with base_url: {self.config.OPENROUTER_BASE_URL}")

    def _extract_call_params(self, call_body: Dict) -> Dict:
        """从 call_body 中提取调用参数"""
        model = call_body.get("model", self.config.DEFAULT_TEXT_MODEL)
        messages = call_body.get("messages", [])
        extra_headers = call_body.get("extra_headers", {})
        extra_body = call_body.get("extra_body", {})
        
        # 从 extra_body 中提取参数
        max_tokens = extra_body.get("max_tokens", self.config.MAX_OUTPUT_TOKENS)
        streaming = extra_body.get("streaming", False)
        response_format = extra_body.get("response_format", None)
        
        return {
            "model": model,
            "messages": messages,
            "extra_headers": extra_headers,
            "max_tokens": max_tokens,
            "streaming": streaming,
            "response_format": response_format,
            "temperature": self.config.TEMPERATURE
        }

    async def generate_text(self, request: GenerationRequest) -> Union[GenerationResponse, StreamingResponse]:
        """
        根据 GenerationRequest 生成文本
        支持一次性输出和流式输出两种模式
        """
        task_info = request.user_call_data.task_info
        task_context = {
            "task_id": task_info.task_id or "-",
            "call_time": task_info.call_time or "-",
        }
        with logger.contextualize(**task_context):
            try:
                logger.info(
                    "Processing generation request user_id={} stream_mode={}",
                    task_info.user_id,
                    request.is_stream,
                )
                if task_info.task_id == "五行命理":
                    call_body = self.fortune_builder.get_call_body(request)
                elif task_info.task_id == "面相分析":
                    call_body = self.face_builder.get_call_body(request)
                else:
                    logger.warning("Unsupported task_id received: {}", task_info.task_id)
                    raise HTTPException(status_code=400, detail="Unsupported task_id")

                is_stream = request.is_stream if request.is_stream is not None else False

                if is_stream:
                    logger.info("Initiating streaming text generation")
                    return StreamingResponse(
                        self._generate_stream(call_body, task_context),
                        media_type="text/plain; charset=utf-8"
                    )
                logger.info("Invoking one-time generation")
                return await self._generate_once(call_body, task_context)

            except HTTPException:
                raise
            except Exception as e:
                logger.exception("Error in text generation")
                raise HTTPException(status_code=500, detail=str(e))

    async def _generate_once(self, call_body: Dict, task_context: Dict[str, str]) -> GenerationResponse:
        """一次性生成文本"""
        with logger.contextualize(**task_context):
            try:
                logger.info("Starting one-time text generation")
                response = await self.async_client.chat.completions.create(**call_body)

                content = response.choices[0].message.content
                usage_info = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

                logger.info("One-time text generation completed")

                return GenerationResponse(
                    success=True,
                    data=content,
                    usage=usage_info
                )

            except Exception as e:
                logger.exception("Error in one-time text generation")
                return GenerationResponse(
                    success=False,
                    error=str(e)
                )

    async def _generate_stream(self, call_body: Dict, task_context: Dict[str, str]) -> AsyncGenerator[bytes, None]:
        """流式生成文本"""
        with logger.contextualize(**task_context):
            try:
                logger.info("Starting streaming text generation")

                params = self._extract_call_params(call_body)

                api_params = {
                    "model": params["model"],
                    "messages": params["messages"],
                    "max_tokens": params["max_tokens"],
                    "temperature": params["temperature"],
                    "stream": True,
                    "extra_headers": params["extra_headers"]
                }

                if params["response_format"]:
                    api_params["response_format"] = params["response_format"]

                stream = await self.async_client.chat.completions.create(**api_params)

                async for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content.encode("utf-8")

                logger.info("Streaming text generation completed")

            except Exception as e:
                logger.exception("Error in streaming text generation")
                yield f"Error: {str(e)}".encode("utf-8")

    def health_check(self) -> HealthResponse:
        """健康检查"""
        try:
            return HealthResponse(
                status="healthy",
                timestamp=str(int(time.time()))
            )
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return HealthResponse(
                status="unhealthy",
                timestamp=str(int(time.time()))
            )


# 创建服务实例
openrouter_service = OpenRouterService()

# 创建 FastAPI 应用
app = FastAPI(
    title="OpenRouter API Service",
    description="基于 OpenRouter 的大模型 API 服务",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _serve_page(page_path: Path, not_found_message: str) -> FileResponse:
    """Serve a static HTML page with existence checks."""
    if not page_path.exists():
        logger.error("Static page not found at {}", page_path)
        raise HTTPException(status_code=404, detail=not_found_message)
    return FileResponse(page_path)


@app.post("/generate", response_model=GenerationResponse)
async def generate_text_endpoint(request: GenerationRequest):
    """
    文本生成接口
    支持一次性输出和流式输出两种模式
    """
    return await openrouter_service.generate_text(request)


@app.get("/health", response_model=HealthResponse)
async def health_check_endpoint():
    """健康检查接口"""
    return openrouter_service.health_check()


@app.get("/face")
async def face_page():
    """面相分析前端页面"""
    return _serve_page(FACE_PAGE_PATH, "face_teller.html 未部署")


@app.get("/fortune")
async def fortune_page():
    """命运测算前端页面"""
    return _serve_page(FORTUNE_PAGE_PATH, "fortune_teller.html 未部署")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "OpenRouter API Service is running",
        "pages": {
            "face": "/face",
            "fortune": "/fortune",
            "api": "/generate",
        },
    }


if __name__ == "__main__":
    import uvicorn
    
    # 启动服务
    uvicorn.run(
        app,
        host=gpt_general_config.API_HOST,
        port=gpt_general_config.API_PORT,
        log_level="info"
    )
