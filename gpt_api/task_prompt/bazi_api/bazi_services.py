import asyncio,traceback,json,httpx
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from gpt_api.logger_setup import logger

from bazi_config import bazi_config
from bazi_models import (
    BaziRequest,
    BaziResponse,
    HealthResponse
)
from bazi import Bazi, BaziAPI
from utils import async_retry, format_timestamp


# 初始化八字服务
bazi = Bazi()


async def periodic_health_check() -> None:
    """定时检查自身健康状态，方便监控日志"""
    url = f"http://{bazi_config.API_HOST}:{bazi_config.API_PORT}/health"
    while True:
        await asyncio.sleep(bazi_config.HEALTH_CHECK_INTERVAL)
        try:
            async with httpx.AsyncClient(timeout=bazi_config.REQUEST_TIMEOUT) as client:
                response = await client.get(url)
                response.raise_for_status()
                logger.debug("八字服务健康检查成功")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("八字服务健康检查失败: {}", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("八字API服务启动中... 监听地址: {}:{}", bazi_config.API_HOST, bazi_config.API_PORT)
    health_task = asyncio.create_task(periodic_health_check())
    try:
        yield
    finally:
        health_task.cancel()
        with suppress(asyncio.CancelledError):
            await health_task
        # 关闭时
        logger.info("八字API服务关闭中...")


app = FastAPI(
    title="八字计算 API 服务",
    description="提供八字计算、真太阳时换算、大运推算等功能的 API 接口",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/bazi/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": format_timestamp(),
        "service": "bazi",
    }


@app.post("/bazi/compute")
@async_retry(max_attempts=3, delay=1.0)
async def compute_bazi(request: BaziRequest):
    """计算八字"""
    try:
        # 验证输入数据
        if not request.birth_datetime or not request.location_name or not request.gender:
            raise HTTPException(status_code=400, detail="缺少必要参数：出生时间、出生地或性别")
        
        # 验证时间格式
        try:
            datetime.strptime(request.birth_datetime, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise HTTPException(status_code=400, detail="出生时间格式错误，应为 'YYYY-MM-DD HH:MM:SS'")
        
        # 验证性别
        gender_lower = request.gender.lower().strip()
        if gender_lower not in ["男", "女", "male", "female", "m", "f"]:
            raise HTTPException(status_code=400, detail="性别仅支持 男/女 或 male/female")
        
        # 调用八字计算服务
        result = bazi.compute_bazi(request.dict())

        data =  BaziResponse(
            success=True,
            data=result,
            usage={"type": "bazi", "location": request.location_name},
            input = result['input'],
            output = result['output'],
            error=None,
        )

        # 直接返回计算结果
        logger.info("八字计算成功: name={}, age={}", request.name, result.get('age', 'N/A'))
        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"八字计算失败: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
        }



@app.get("/bazi/info")
async def get_service_info():
    """获取服务信息"""
    return {
        "service": "八字计算 API",
        "version": "1.0.0",
        "description": "提供八字计算、真太阳时换算、大运推算等功能",
        "endpoints": {
            "compute": "POST /compute - 完整八字计算",
            "compute_simple": "POST /compute/simple - 简化八字计算",
            "health": "GET /health - 健康检查",
            "info": "GET /info - 服务信息",
        },
        "features": [
            "八字四柱计算",
            "真太阳时换算",
            "大运推算",
            "农历转换",
            "地理位置编码",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "bazi_services:app",
        host=bazi_config.API_HOST,
        port=bazi_config.API_PORT,
        reload=True,
        log_config=None,
    )
