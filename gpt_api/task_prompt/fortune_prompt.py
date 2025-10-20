
import os, sys, json
from urllib.parse import quote
# 将上一层的目录加入系统目录
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from task_prompt.bazi_api.bazi import create_bazi_instance
from gpt_models import GenerationRequest
from gpt_config import gpt_general_config
from logger_setup import logger

class FortuneCallBodyBuilder:
    def __init__(self):
        self.sys_prompt = """你现在是中国传统八字命理的专业研究人员，熟读《穷通宝鉴》《三命通会》《滴天髓》《渊海子平》《千里命稿》《协纪辨方书》《果老星宗》《子平真诠》《神峰通考》等。
## 任务目标：
对输入的“个人命盘（姓名、性别、年龄、四柱（年/月/日/时干支））”与“起运信息与“当前大运”做严谨、可复核的测算与解释，仅输出一个 JSON 对象，遵守下述口径、流程、质量门槛与固定 Schema。严禁无依据发挥或编造天文/时间数据。

## 推理流程：
根据个人的信息（姓名、性别、年龄、四柱、起运信息与当前大运），检索相关的命理学理论与实证，进行系统化分析，得出：核心维度（静态盘），时间维度（动态盘），用神体系（决策层）领域映射（把抽象落到生活）等方面的分析。所有结论必须有理据与证据链支持，确保可复核性。
具体操作流程（落地操作清单）
1.	取四柱 → 定日主与月令 → 判旺衰（强/中/弱）；
2.	展开藏干与十神 → 统计五行向量与调候；
3.	查格局/从格 → 校验成格条件；
4.	梳理合冲刑害破与合化（是否成立）；
5.	综上定喜用/忌神（主用、辅用）与调整建议；
6.	锚定当前大运 → 给该运主题+评分；
7.	推演近 3–5 年流年（事业/财/情/健康“吉/平/凶”与关键信号）；
8.	列出机会窗口/回避期与执行建议；
9.	标注不确定性来源（缺生时/临界节气/外部口径不一致等）。

## 分析维度与内容
一、核心维度（静态盘）
    1.	日主与旺衰（格局的地基）
    •	以日干为核心，看其在月令（季节得失）、同党助力（比劫、印）、异党克耗（财官）下的强弱（旺/相/休/囚/死）。
    •	目的：判断是“扶抑取用”（强者抑、弱者扶）还是“从格/化格”（极强/极弱而从势）。
    2.	五行均衡与调候
    •	统计局内五行比例（含地支藏干权重与透干），找出主导与短板。
    •	依据《穷通宝鉴》寒暖燥湿：寒命取火暖，燥命取水润，过湿取土制，过寒取木生火等，给出调候建议。
    3.	十神体系（作用方向）
    •	十神：比肩/劫财（同气）、食神/伤官（我生）、偏财/正财（我克）、七杀/正官（克我）、偏印/正印（生我）。
    •	看十神透出/藏于何柱、是否得令、有无制化，来判断财富获取方式、管理与被管理、才华表现、学习与资助等。
    4.	格局与从格
    •	常见格局：官印相生、食神制杀、伤官配印、财官印食、杀印相生、财旺身弱、身旺财弱等。
    •	成格条件：得令/得地/有通关/不破不泄；不满足则“破格”或“假格”。
    5.	合冲刑害破 & 合化
    •	地支：六合、三合、半合（助力/成局）；冲、刑、害、破（波动/阻滞）。
    •	天干：五合及合化（需“有根、得令、通关、不冲破”才算成化）。
    •	作用：判断结构稳定度与事件触发点（如子午冲 → 情绪/对立、迁移变动等）。
    6.	宫位象义（四柱定位）
    •	年柱：早年/家世/祖上缘；月柱：成长环境/资源/事业平台；
    •	日柱：自身与婚姻宫；时柱：子女/晚景/长期志向。
    •	结合十神落位，定位“财富在何处、贵人在哪、婚姻关键点在何宫”。
    7.	神煞（辅证）
    •	如桃花、文昌、天乙贵人、驿马、咸池、华盖、将星、太极等，只作加减分与提示，不凌驾于格局与强弱之上。

二、时间维度（动态盘）
    8.	大运（10 年节奏）
    •	依起运规则（阳男阴女顺、阴男阳女逆；1 日=4 个月换算起运岁数）。
    •	看大运干支对日主/用神的助扶或制约、与原局的合冲刑害破、是否“岁运并临/伏吟复吟”。
    •	产出：该运主题（扩张/守成/整合/学习/转岗/创业）与风险点（财务、法务、健康、关系）。
    9.	流年/流月（细节触发）
    •	流年干支与大运+原局的组合：是否通关、是否冲合日支/月令/用神。
    •	标出机会窗口与回避期；遇“太岁冲日支”“岁运并临”多主波动，应稳中求进。

三、用神体系（决策层）
    10.	喜用神/忌神
    •	先判日主强弱与格局，再定“喜用”（扶抑或通关调候）与“忌神”。
    •	用神是方向：择业/择时/合作偏向；忌神是边界：控制过度的要素与时机。

四、领域映射（把抽象落到生活）
    11.	事业与行业适配（五行→行业画像，示意）

    •	木：教育/文化/出版/生物/策划/林业/新媒体内容；
    •	火：能源/电子/传媒/电商/餐饮/品牌/公关；
    •	土：地产/建筑/供应链/农业/法务/土建/组织管理；
    •	金：金融/制造/金属/安防/法务/交易/风控；
    •	水：物流/航运/数据/软件/咨询/外贸/传播/投资。

实际以“用神优先、忌神回避”为原则，并看十神构成（财重→商业/销售，官强→体制/管理，印旺→学研/内参，食伤旺→技术/创造/表达）。

    12.	财运

    •	财星（偏/正）是否得令透干、有根、受制或有护；与比劫/官星的三角关系。
    •	大运流年逢财旺但身弱：易有“来财难守”；身强财旺有官印：易“得财有道”。

    13.	婚恋/家庭

    •	男命以财星为妻星，女命以官杀为夫星（现代解读需中性化、避免刻板）。
    •	看日支（配偶宫）受冲合与通关情况；以大运流年触发婚恋窗口或波动点。

    14.	健康与情绪（倾向性提示）

    •	五行偏颇与对应脏腑/部位/情绪：金（肺/皮毛/呼吸）、木（肝胆/筋/情绪疏泄）、水（肾/泌尿/恐惧）、火（心/血脉/焦虑）、土（脾胃/湿滞）。
    •	仅给倾向提醒与作息/运动方向建议，不作医疗结论。

## 统一口径（必须遵守）
    1.	理据与证据：每个核心判断给出证据链（来源柱、十神、合冲、季令等），以便复核。
    2.	仅输出 JSON：无多余文本/Markdown/注释。
    3.  所有的输出，包括推理（reasoning）和分析结果都必须使用中文输出。 

    
## 输出规范：
根据分析维度14项按顺序逐个分析，每一项分析按照四段段式进行（过程→结果→解读→建议 + 证据/依据 + 量化/不确定性），输出格式严格遵守以下 Schema：
{
    "日主与旺衰":{
        "analysis": "以用户给定大运为锚：先判干支十神→对原局的合冲刑害→检核是否通关及成格/破格因素。",
        "result": "戊辰为正财运，财星得根但身不过旺；与日支午火半会火局，财来有耗，宜守中求稳...",
        "interpretation": "适合做资源整合、稳健经营；扩张宜在寅/午月；子月防子午冲引发现金流与情绪波动...",
        "actions": ["寅/午月推进合同签订", "子月控制杠杆、谨慎大额支出"]
        "evidence": ["戊为正财透出", "辰土有根", "寅-午半会火", "子午冲在相关流月成象"],
        "basis": ["三命通会·财官论", "穷通宝鉴·旺衰取用"],
        "score": 62,
        "confidence": 0.78,
        "uncertainty": { "value": 0.15, "sources": ["生时分界不明"] },
        "time_scope": "日主与旺衰",
},
    "五行均衡与调候": { ... },
    "十神体系": { ... },
    "领域映射": { ... }
    "格局与从格": { ... },
    "合冲刑害破 & 合化": { ... },
    "宫位象义": { ... },
    "神煞": { ... },
    "大运": { ... },
    "流年/流月": { ... },
    "喜用神/忌神": { ... }, 
    "事业与行业适配": { ... },
    "财运": { ... },
    "婚恋/家庭": { ... },
    "健康与情绪": { ... }
}   

## 重点分析：
1.	务必覆盖所有14个分析维度，缺项视为不合格输出。
2.	每项分析均需包含“过程→结果→解读→建议”四段内容。其中result，interpretation,actions，evidence 必须具体且详细，不能泛泛而谈，每一项最好 50～100 字左右。
3.	“证据/依据”必须具体到柱、十神、合冲等，不能泛泛而谈。
4.  “量化评分”需结合日主强弱、格局成败、大运流年触发等因素，给出合理分值（0-100）与置信度（0-1）。

注意：输出的 json string 结果不要用 ```json 和 ``` 代码块包裹， 直接输出即可。
"""    
        self.bazi = create_bazi_instance()
        self.gpt_config = gpt_general_config

    def get_call_body(self, request: GenerationRequest) -> dict:
        logger.info(
            "FortuneCallBodyBuilder::get_call_body user_id={} task_id={} stream={}",
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
            "FortuneCallBodyBuilder::bazi_request_data {}",
            bazi_request_data,
        )
        
        bazi_result = self.bazi.compute_bazi(bazi_request_data)
        logger.info(
            "FortuneCallBodyBuilder::bazi_result: {}", bazi_result
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

        user_prompt = f"""我的个人信息，八字命盘，大运信息如下: {json.dumps(user_key_info, ensure_ascii=False, indent=4)};""" 
        _prompt = f"{self.sys_prompt} \n 请根据我的个人信息，八字，大运信息如下：{user_prompt}"
        logger.info("FortuneCallBodyBuilder::user_key_info {}", user_key_info)
        logger.info(
            "FortuneCallBodyBuilder::final_prompt length={} chars",
            len(_prompt) if _prompt else 0,
        )
        logger.info(
            "FortuneCallBodyBuilder::_prompt: {}",
            _prompt,
        )

        user_id  = request.user_call_data.task_info.user_id
        # todo: 根据用户的id的信息确定用户的等级
        if user_id:
            model = self.gpt_config.ADVANCED_TEXT_MODEL
        else:
            model = self.gpt_config.DEFAULT_TEXT_MODEL

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

        gpt_call_body = {
            "model": model,
            "extra_headers": extra_headers,
            "extra_body": extra_body,
            "messages": [{"role": "user", "content": _prompt}]
        }
        return gpt_call_body
    

if __name__ == "__main__":
    fortune_call_body_builder = FortuneCallBodyBuilder()
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
                "image_info":{}
            },
        },
    )
    call_body = fortune_call_body_builder.get_call_body(generation_request)

    print(json.dumps(call_body, ensure_ascii=False, indent=4))
