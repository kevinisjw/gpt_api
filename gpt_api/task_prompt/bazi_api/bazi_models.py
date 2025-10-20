from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class BaziRequest(BaseModel):
    """八字计算请求模型"""
    birth_datetime: str = Field(..., description="出生时间，格式 YYYY-MM-DD HH:MM:SS")
    location_name: str = Field(..., description="出生地（用于地理编码）")
    gender: str = Field(..., description="性别，支持 男/女 或 male/female")
    name: str = Field(..., description="姓名")

class BaziResponse(BaseModel):
    """八字响应模型"""
    success: bool = Field(..., description="是否成功")
    error: Optional[str] = Field(None, description="错误信息")
    usage: Optional[Dict[str, Any]] = Field(None, description="使用情况")
    input: Optional[Dict[str, Any]] = Field(None, description="输入数据")
    output: Optional[Dict[str, Any]] = Field(None, description="输出数据")
    user_key_info: Optional[Dict[str, Any]] = Field(None, description="用户关键信息提示词")

class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    timestamp: str = Field(..., description="时间戳")
    service: str = Field(..., description="服务名称")
