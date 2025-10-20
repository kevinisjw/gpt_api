from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from enum import Enum

class OutputType(str, Enum):
    TEXT = "text"
    IMAGE = "image"

class TaskInfo(BaseModel):
    user_id: str                    = Field(..., description="用户id")
    call_id: str                    = Field(..., description="用户请求调用 id, 全局唯一")
    call_time: str                  = Field(..., description="用户请求调用时间")
    call_ip: str                    = Field(..., description="用户请求调用ip")
    task_id: str                    = Field(..., description="用户请求任务名称 id, 用于匹配 prompt和模型")

class UserInputInfo(BaseModel):
    text_info: Optional[Dict[str, Any]]  = Field(None, description="文本输入信息")
    image_info: Optional[Dict[str, Any]] = Field(None, description="图片输入信息")

class UserCallData(BaseModel):
    # 任务信息
    task_info: TaskInfo             = Field(..., description="任务信息")

    # 用户输入信息
    user_input_info: UserInputInfo = Field(..., description="用户输入信息")


class GenerationRequest(BaseModel):
    is_stream: Optional[bool]       = Field(None, description="是否流式输出")    
    user_call_data: UserCallData    = Field(None, description="用户请求信息") # 用户需要传入模型所有数据    

class GenerationResponse(BaseModel):
    success: bool        = Field(..., description="是否成功")
    data: Optional[str]  = Field(None, description="生成的数据")
    error: Optional[str] = Field(None, description="错误信息")
    usage: Optional[Dict[str, Any]] = Field(None, description="使用情况")

class HealthResponse(BaseModel):
    status: str = Field(..., description="服务状态")
    timestamp: str = Field(..., description="时间戳")


if __name__ == "__main__":
    request = GenerationRequest(
        is_stream = False,
        user_call_data={
            "task_info": {
                "user_id": "test_user",
                "call_id": "test_call",
                "call_time": "2023-01-01 00:00:00",
                "call_ip": "127.0.0.1",
                "task_id": "test_task",
            },
            "user_input_info": {
                "text_info": {
                    "birth_datetime": " 1989-10-28 12:00:00",
                    "location_name": "中国南宁市",
                    "gender": "女",
                    "name": "王鸥"
                },
                "image_info": {
                    "image_url_list": ["https://example.com/image.jpg"],
                }
            },
        }
    )
    print(request)