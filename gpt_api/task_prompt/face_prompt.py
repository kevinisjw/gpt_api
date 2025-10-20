import os, sys, json, base64
from urllib.parse import quote
# 将上一层的目录加入系统目录
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from task_prompt.bazi_api.bazi import create_bazi_instance
from gpt_models import GenerationRequest
from gpt_config import gpt_general_config
from logger_setup import logger

class FaceCallBodyBuilder:
    def __init__(self):
        self.sys_prompt = """你是一名中国传统相面术 + 子平命理（生辰八字）的研究者与实践者，需在一张人脸图像与个人八字的合参条件下，给出**可复核、仅含 JSON 字符串（仅 domains 键）**的面向分析结论。结论定位于“结构与阶段信号”，不提供医学/法律/财务诊断。若信息缺失或存在干扰（妆容/强光/畸变/遮挡/整形/疲劳/用药等），必须在证据与评分中反映并降低置信度。

【理论依据｜原典与纲要（作为引用来源清单，输出时写入各维度的 basis）】
《神相全编》《麻衣相法》《柳庄相法》《相理衡真》《神相铁关刀》《水镜神相》《月波洞中记》；方法学术语对照可参考《中医诊断学·望诊》（仅作观察术语与部位对照，不凌驾于相法原典）。

【输入规范（模型先标准化）】
	•	image: 1 张正面自然光无遮挡人脸照（可选再加侧面/自然表情短视频 5–10 秒，仅用于“动相/声相”判断）。
	•	bazi: 生辰八字（年/月/日/时干支）+（若有）起运方式/起运年龄/当前大运。
    •	如果输入的不是人脸，或者人脸的质量不高，图像不清晰，可以拒绝回到答，并在 analysis 中说明原因。

若图像与文本冲突：短期状态以面相为主，结构周期以八字为主；在 evidence 中分别以 face: 与 bazi: 标注来源，并在评分与置信度中体现冲突。

【作业流程（在各维度的 analysis 字段中如实呈现“过程”）】
	1.	取像质控：光线/角度/遮挡/妆容/畸变/分辨率检查。
	2.	总纲五要：形/神/气/骨/色快速打标（指出主导信号与短板）。
	3.	结构比例：三庭五眼、对称度、面型五行（可为混合型，给出主次）。
	4.	五官组合：眉-眼-鼻-口-耳的坐标与呼应（“鼻配颧、口配地阁、耳应额”）。
	5.	十二宫巡检：命/官禄/财帛/夫妻/子女/田宅/迁移/疾厄/福德/父母/兄弟/奴仆等关键位的饱满度、光泽、纹理与对称。
	6.	气色与纹理：印堂/山根/颧/鼻头/唇色/眼白之明润/晦暗/暴色；法令/鱼尾/额纹/山根纹走向与断续。
	7.	动相与声相：目光聚散、表情收放、肩背开合、步态、音色与共鸣。
	8.	八字合参：以八字定结构（喜用/忌神、事业/财/婚等主题）与大运/流年节奏；核对与面相信号的同/背离，并给“择时/节奏”建议。
	9.	不确定性与复检：列明冲突/干扰项与可能影响，提出复检时间窗口或改进采样方式。

【命运主题（仅输出以下 7 项；逐项采用“过程→结果→解读→建议+证据/依据+量化”的四段式）】
	•	财运
	•	事业
	•	婚恋
	•	子女
	•	健康
	•	贵人与人脉
	•	晚景与养老

【证据与量化要求】
	•	每个主题都必须给出：
	•	analysis：按“流程”展开的观察与合参过程（含质控结果）。
	•	result：≥50 字的结构化结论（指出强弱、阶段与边界）。
	•	interpretation：≥50 字的策略性解读（如何取舍与节奏）。
	•	actions：2–5 条可执行建议（含择时/节律/资源配置）。
	•	evidence：≥4 条、且至少各含 1 条 face 与 1 条 bazi，精确到部位/信号/干支/大运流年，如：
	•	face: 鼻头细润、鼻翼收放有度；印堂明润，无横纹
	•	bazi: 身强财旺，有官印护；当前大运偏财透出，流年冲合配偶宫
	•	basis：从原典清单中择 1–3 部（可加“望诊术语对照”）。
	•	score：0–100（60=中性可行，>75=较优，<50=需谨慎）。
	•	confidence：0–1（依图像质量/冲突程度/证据一致性调整）。
	•	time_scope：清晰时间窗（如“当前—3个月/6–12个月/1–3年/长期”）。

【禁止与边界】
	•	禁止输出除 JSON 字符串 以外的任何内容（含前后缀文字与 Markdown 代码块）。
	•	禁止编造不可见信息与医学/法律/财务诊断；可给就医/法务/财务顾问的“转介式建议”。
	•	未知即标注在 evidence 与 analysis 中，并在 confidence 下调。

【固定输出 Schema（仅此一层；键名必须一致；值由模型填充）】
{
“财运”: { “analysis”:””, “result”:””, “interpretation”:””, “actions”:[], “evidence”:[], “basis”:[], “score”:0, “confidence”:0, “time_scope”:”” },
“事业”: { “analysis”:””, “result”:””, “interpretation”:””, “actions”:[], “evidence”:[], “basis”:[], “score”:0, “confidence”:0, “time_scope”:”” },
“婚恋”: { “analysis”:””, “result”:””, “interpretation”:””, “actions”:[], “evidence”:[], “basis”:[], “score”:0, “confidence”:0, “time_scope”:”” },
“子女”: { “analysis”:””, “result”:””, “interpretation”:””, “actions”:[], “evidence”:[], “basis”:[], “score”:0, “confidence”:0, “time_scope”:”” },
“健康”: { “analysis”:””, “result”:””, “interpretation”:””, “actions”:[], “evidence”:[], “basis”:[], “score”:0, “confidence”:0, “time_scope”:”” },
“贵人与人脉”: { “analysis”:””, “result”:””, “interpretation”:””, “actions”:[], “evidence”:[], “basis”:[], “score”:0, “confidence”:0, “time_scope”:”” },
“晚景与养老”: { “analysis”:””, “result”:””, “interpretation”:””, “actions”:[], “evidence”:[], “basis”:[], “score”:0, “confidence”:0, “time_scope”:”” }
}

【生成规则（再次强调）】
	•	使用中文输出；
	•	严格只返回一个 JSON 字符串，且仅包含上述 domains 键及其子项；
	•	若信息冲突或质控不达标，务必在 analysis/evidence 中写明，并通过 score/confidence/time_scope 反映“延后/复检/择时”的建议。
    •	直接输出 json string，不要用 ```json ``` 代码块包裹。
"""
        self.bazi = create_bazi_instance()
        self.gpt_config = gpt_general_config
        
    def get_call_body(self, request: GenerationRequest) -> dict:
        logger.info(
            "FaceCallBodyBuilder::get_call_body user_id={} task_id={} stream={}",
            request.user_call_data.task_info.user_id,
            request.user_call_data.task_info.task_id,
            request.is_stream,
        )
        bazi_request_data = {
            "birth_datetime": request.user_call_data.user_input_info.text_info['birth_datetime'],
            "location_name": request.user_call_data.user_input_info.text_info['location_name'],
            "gender":request.user_call_data.user_input_info.text_info['gender'],
            "name": request.user_call_data.user_input_info.text_info['name']
        }
        logger.info(
            "FaceCallBodyBuilder::bazi_request_data {}",
            bazi_request_data,
        )
        logger.info(
			"FaceCallBodyBuilder::bazi_request_data: {}",
			bazi_request_data,
		)
        
        bazi_result = self.bazi.compute_bazi(bazi_request_data)
        logger.info(
            "FaceCallBodyBuilder::bazi_result: {}", bazi_result
        )
        user_key_info = {
            "姓名": bazi_result.get("input", {}).get("name", ""),
            "年龄": bazi_result.get("output", {}).get('meta', {}).get("age", ""),
            "性别": bazi_result.get("output", {}).get('meta', {}).get("gender", {}).get("label", ""),
            "我的八字": bazi_result.get("output", {}).get("bazi", ""),
            "今日干支信息": bazi_result.get("output", {}).get("today_ganzhi", ""),
            "大运起运年龄": bazi_result.get("output", {}).get("fortune", {}).get("current_fortune_stage", {}).get("start_age", ""),   
            "当前大运": bazi_result.get("output", {}).get("fortune", {}).get("current_fortune_stage", {}).get("luck", ""),
            "当前大运周期": bazi_result.get("output", {}).get("fortune", {}).get("current_fortune_stage", {}).get("period", ""),
        }
	
        user_prompt = f"""{json.dumps(user_key_info, ensure_ascii=False, indent=4)}""" 
        _prompt = f"{self.sys_prompt} \n 个人信息，八字，大运信息如下：{user_prompt}; \n人脸图像如图所示，请基于此进行面相分析，并严格按照要求的 JSON schema 输出结果。"
        logger.info("FaceCallBodyBuilder::user_key_info: {}", user_key_info)
        logger.info("FaceCallBodyBuilder::final_prompt length={} chars", len(_prompt) if _prompt else 0)
        logger.info("FaceCallBodyBuilder::_prompt length={}", _prompt)

        user_id  = request.user_call_data.task_info.user_id
        # todo: 根据用户的id的信息确定用户的等级
        if user_id:
            model = self.gpt_config.ADVANCED_IMAGE_MODEL
        else:
            model = self.gpt_config.DEFAULT_IMAGE_MODEL

        max_output_tokens = self.gpt_config.MAX_OUTPUT_TOKENS   
        task_id = request.user_call_data.task_info.task_id
        safe_task_id = quote(task_id, safe="")

        extra_headers = {
            "HTTP-Referer": f"http://example.com/tasks/{safe_task_id}", # Optional. Site URL for rankings on openrouter.ai.
            "X-Title": safe_task_id, # Optional. Site title for rankings on openrouter.ai.
        }
        extra_body = {
            "streaming" : self.gpt_config.IS_STREAM,
            "max_tokens" : max_output_tokens ,
            "modalities" : ['text'],
            "response_format" : { "type": "json_object" }
        }
        b64_img = request.user_call_data.user_input_info.image_info['image_url'][0]
        logger.info(
            "FaceCallBodyBuilder::image_payload length={} chars",
            len(b64_img) if b64_img else 0,
        )
        data_uri = f"data:image/jpeg;base64,{b64_img}"
        
        gpt_call_body = {
            "model": model,
            "extra_headers": extra_headers,
            "extra_body": extra_body,
            "messages": [
                {
                    "role": "user",
                  	"content": [
                		{"type": "text", "text": _prompt},
						{"type": "image_url", "image_url": {"url": data_uri, "detail": "auto"}},
					]
                }
            ]
        }
        return gpt_call_body
    

if __name__ == "__main__":
    face_path = "/Users/bytedance/Desktop/王鸥.jpg"
    with open(face_path, "rb") as image_file:
         image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
          
    face_call_body_builder = FaceCallBodyBuilder()
    
    generation_request = GenerationRequest(
        is_stream = True,
        user_call_data={
            "task_info": {
                "user_id": "123456789",
                "call_id": "123",
                "call_time": "2023-01-01 00:00:00",
                "call_ip": "127.0.0.1",
                "task_id": "五行命理",
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
    call_body = face_call_body_builder.get_call_body(generation_request)

    print(json.dumps(call_body, ensure_ascii=False, indent=4))
