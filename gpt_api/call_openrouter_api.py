"""
Example client that invokes `OpenRouterService.generate_text` directly without
going through the FastAPI HTTP layer.
"""

import asyncio
import json,base64
from typing import Union

from fastapi.responses import StreamingResponse

from gpt_models import GenerationRequest, GenerationResponse
from gpt_services import openrouter_service


def build_generation_request() -> GenerationRequest:
    face_path = "./images/王鸥.jpg"
    with open(face_path, "rb") as image_file:
         image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
    
    face_request = GenerationRequest(
        is_stream = True,
        user_call_data={
            "task_info": {
                "user_id": "123456789",
                "call_id": "123",
                "call_time": "2023-01-01 00:00:00",
                "call_ip": "127.0.0.1",
                "task_id": "面相分析",
            },
            "user_input_info": {
                "text_info": {
                    "birth_datetime": "2000-01-01 00:00:00",
                    "location_name": "北京市",
                    "gender": "男",
                    "name": "张三",
                },
                "image_info":{
                    "image_url": [image_base64],
                    "image_type": "base64"
				}
            },
        },
    )

    # fortune_request = GenerationRequest(
    #     is_stream=False,
    #     user_call_data={
    #         "task_info": {
    #             "user_id": "123456789",
    #             "call_id": "12345",
    #             "call_time": "2023-01-01 00:00:00",
    #             "call_ip": "127.0.0.1",
    #             "task_id": "五行命理",
    #         },
    #         "user_input_info": {
    #             "text_info": {
    #                 "birth_datetime": " 1989-10-28 12:00:00",
    #                 "location_name": "中国南宁市",
    #                 "gender": "女",
    #                 "name": "王鸥",
    #             },
    #             "image_info": {
    #                 "image_url_list": ["https://example.com/image.jpg"],
    #             },
    #         },
    #     },
    # )
    return face_request


async def call_generate_endpoint(
    request: GenerationRequest,
) -> Union[GenerationResponse, None]:
    """
    Call `OpenRouterService.generate_text` and print the result.

    If streaming is enabled the function consumes the stream and prints the
    chunks as they arrive. Otherwise it prints the JSON payload.
    """
    result = await openrouter_service.generate_text(request)

    if isinstance(result, StreamingResponse):
        print("----------------Streaming response:")
        async for chunk in result.body_iterator:
            if isinstance(chunk, bytes):
                print(chunk.decode("utf-8"), end="", flush=True)
            else:
                print(str(chunk), end="", flush=True)
        return None

    if isinstance(result, GenerationResponse):
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
        return result

    raise TypeError(f"Unexpected response type: {type(result)}")


async def main() -> None:
    request = build_generation_request()
    await call_generate_endpoint(request)


if __name__ == "__main__":
    asyncio.run(main())
