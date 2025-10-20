"""
八字计算核心模块 - 重构版本
基于 bazi_main.py 和 bazi_service.py 重构，提供统一的 Bazi 类接口

功能：
1. 八字计算（四柱干支）
2. 真太阳时换算
3. 大运推算
4. 农历转换
5. API接口封装
"""

import json
import logging
import math
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from dateutil.relativedelta import relativedelta
from lunarcalendar import Converter, Lunar, Solar, DateNotExist
from lunarcalendar.solarterm import zh_solarterms
from pydantic import BaseModel, Field, ValidationError, validator


# ============================================================================
# 常量和配置
# ============================================================================

TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 年干对应的正月天干索引
FIRST_MONTH_STEM_MAP: Dict[int, int] = {
    0: 2, 5: 2,  # 甲己年正月为丙寅
    1: 4, 6: 4,  # 乙庚年正月为戊寅
    2: 6, 7: 6,  # 丙辛年正月为庚寅
    3: 8, 8: 8,  # 丁壬年正月为壬寅
    4: 0, 9: 0,  # 戊癸年正月为甲寅
}

# 日干对应的子时天干索引
RAT_HOUR_STEM_MAP: Dict[int, int] = {
    0: 0, 5: 0,  # 甲己日子时为甲子
    1: 2, 6: 2,  # 乙庚日子时为丙子
    2: 4, 7: 4,  # 丙辛日子时为戊子
    3: 6, 8: 6,  # 丁壬日子时为庚子
    4: 8, 9: 8,  # 戊癸日子时为壬子
}

# 十二主节气
MAJOR_SOLAR_TERMS = [
    "立春", "惊蛰", "清明", "立夏", "芒种", "小暑",
    "立秋", "白露", "寒露", "立冬", "大雪", "小寒"
]

# 阳干
YANG_STEMS = {"甲", "丙", "戊", "庚", "壬"}

# 默认高德API密钥
DEFAULT_GAODE_API_KEY = "2cd4e12a0bc627d900242b0ea6e10c65"


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class BaziRequest:
    """八字计算请求数据"""
    birth_datetime: str
    location_name: str
    gender: str
    name: str


@dataclass
class FestivalInfo:
    """节气信息"""
    date: date
    name_zh: str
    days_to_today: int


@dataclass
class DateConversionResult:
    """日期转换结果"""
    status: int
    msg: str
    solar: Optional[Solar] = None
    lunar: Optional[Lunar] = None


class BaziRequestModel(BaseModel):
    """八字计算请求模型"""
    birth_datetime: str = Field(..., description="出生时间，格式 YYYY-MM-DD HH:MM:SS")
    location_name: str = Field(..., description="出生地（用于地理编码）")
    gender: str = Field(..., description="性别，支持 男/女 或 male/female")
    name: str = Field(..., description="姓名")

    @validator("birth_datetime")
    def validate_birth_datetime(cls, value: str) -> str:
        val = value.strip()
        try:
            datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            raise ValueError("出生时间格式错误，应为 'YYYY-MM-DD HH:MM:SS'") from exc
        return val

    @validator("location_name", "name")
    def ensure_non_empty(cls, value: str) -> str:
        val = value.strip()
        if not val:
            raise ValueError("字段不能为空")
        return val

    @validator("gender")
    def normalize_gender(cls, value: str) -> str:
        return _normalize_gender(value)


class GanZhiModel(BaseModel):
    """干支模型"""
    year: str
    month: str
    day: str
    hour: str


class FortuneStageModel(BaseModel):
    """大运阶段模型"""
    cycle_index: int
    luck: str
    start_age: float
    end_age: float
    period: str
    is_current: bool
    direction: Optional[str] = None


class FortuneCalculationModel(BaseModel):
    """大运计算模型"""
    rule: str
    target_term: str
    delta_days: float
    delta_hours: float
    start_luck_age: float


class FortuneSummaryModel(BaseModel):
    """大运汇总模型"""
    direction: str
    start_age: float
    start_time: str
    current_luck: str
    current_stage: FortuneStageModel
    timeline: List[FortuneStageModel]
    calculation: FortuneCalculationModel


class LocationModel(BaseModel):
    """位置模型"""
    longitude: float
    latitude: float


class GenderInfoModel(BaseModel):
    """性别信息模型"""
    code: str
    label: str


class MetaModel(BaseModel):
    """元数据模型"""
    age: int
    name: str
    gender: GenderInfoModel


class OutputModel(BaseModel):
    """输出模型"""
    solar_datetime: str
    true_solar_time: str
    lunar_date: str
    birth_time_hms: str
    bazi: GanZhiModel
    today_ganzhi: GanZhiModel
    fortune: FortuneSummaryModel
    location: LocationModel
    meta: MetaModel


class InputEchoModel(BaseModel):
    """输入回显模型"""
    birth_datetime: str
    location_name: str
    gender: str
    name: str


class BaziResponseModel(BaseModel):
    """八字响应模型"""
    input: InputEchoModel
    output: OutputModel


# ============================================================================
# 工具函数
# ============================================================================

def _normalize_gender(value: str) -> str:
    """性别归一化"""
    raw = value.strip()
    if not raw:
        raise ValueError("性别不能为空")

    lower = raw.lower()
    if raw == "男" or lower in {"male", "m"}:
        return "male"
    if raw == "女" or lower in {"female", "f"}:
        return "female"
    raise ValueError("性别仅支持 男/女 或 male/female")


class CallIdAdapter(logging.LoggerAdapter):
    """带调用ID的日志适配器"""
    def process(self, msg, kwargs):
        call_id = self.extra.get("call_id", "unknown")
        return f"[{call_id}] {msg}", kwargs


# ============================================================================
# 核心计算类
# ============================================================================

class LunarCalendarTool:
    """农历转换工具"""

    @staticmethod
    def _lookup_festival_3year(theday: date, term_list) -> List[FestivalInfo]:
        """查找三年内的节气"""
        y = theday.year
        items: List[FestivalInfo] = []
        for yr in (y - 1, y, y + 1):
            for fest in term_list:
                try:
                    d = fest(yr)
                    items.append(
                        FestivalInfo(
                            date=d,
                            name_zh=fest.get_lang("zh"),
                            days_to_today=abs((d - theday).days),
                        )
                    )
                except Exception:
                    continue
        return sorted(items, key=lambda x: x.days_to_today)

    def solar_to_lunar(self, y: int, m: int, d: int) -> DateConversionResult:
        """公历转农历"""
        try:
            solar = Solar(y, m, d)
            lunar = Converter.Solar2Lunar(solar)
            return DateConversionResult(status=1, msg="OK", lunar=lunar, solar=solar)
        except DateNotExist as exc:
            return DateConversionResult(status=-1, msg=f"日期不存在: {exc}")
        except Exception as exc:
            return DateConversionResult(status=-1, msg=f"公转农失败: {exc}")

    def lunar_to_solar(self, y: int, m: int, d: int, is_leap: bool = False) -> DateConversionResult:
        """农历转公历"""
        try:
            lunar = Lunar(y, m, d, isleap=is_leap)
            solar = Converter.Lunar2Solar(lunar)
            return DateConversionResult(status=1, msg="OK", lunar=lunar, solar=solar)
        except DateNotExist as exc:
            return DateConversionResult(status=-1, msg=f"农历日期不存在: {exc}")
        except Exception as exc:
            return DateConversionResult(status=-1, msg=f"农转公失败: {exc}")

    def get_specify_solarterm(self, year: int, name: str) -> Optional[date]:
        """获取指定节气日期"""
        for fest in zh_solarterms:
            zhname = fest.get_lang("zh")
            if zhname == name or (name in zhname and len(name) / max(len(zhname), 1) > 0.5):
                try:
                    return fest(year)
                except Exception:
                    return None
        return None

    def nearest_major_terms_around(self, dt: datetime) -> Tuple[Optional[datetime], Optional[datetime]]:
        """获取出生时刻前后的最近主节气"""
        prev_term: Optional[datetime] = None
        next_term: Optional[datetime] = None
        for yr in (dt.year - 1, dt.year, dt.year + 1):
            for fest in zh_solarterms:
                nm = fest.get_lang("zh")
                if nm not in MAJOR_SOLAR_TERMS:
                    continue
                try:
                    d = fest(yr)
                except Exception:
                    continue
                term_dt = datetime(d.year, d.month, d.day)
                if term_dt < dt and (prev_term is None or term_dt > prev_term):
                    prev_term = term_dt
                if term_dt > dt and (next_term is None or term_dt < next_term):
                    next_term = term_dt
        return prev_term, next_term


class SolarTimeCalculator:
    """真太阳时计算器"""

    def __init__(self, gaode_api_key: str, logger: logging.Logger):
        self.gaode_api_key = gaode_api_key
        self.tool = LunarCalendarTool()
        self.logger = logger

    def get_location_coordinates(self, location_name: str) -> Tuple[float, float]:
        """获取地理位置坐标"""
        self.logger.info("[GEO] 开始定位 | address='%s'", location_name)
        url = "https://restapi.amap.com/v3/geocode/geo"
        params = {"key": self.gaode_api_key, "address": location_name, "output": "JSON"}
        try:
            res = requests.get(url, params=params, timeout=8)
            res.raise_for_status()
            data = res.json()
            if data.get("status") == "1" and data.get("count") != "0":
                loc = data["geocodes"][0]["location"].split(",")
                lng, lat = float(loc[0]), float(loc[1])
                self.logger.info("[GEO] 定位成功 | lng=%.6f, lat=%.6f", lng, lat)
                return lng, lat
            raise ValueError(f"高德未返回有效坐标，响应={data}")
        except Exception as exc:
            self.logger.error("[GEO] 定位失败 | err=%s", exc)
            raise

    def calculate_true_solar_time(self, local_dt: datetime, longitude: float) -> datetime:
        """计算真太阳时"""
        if not isinstance(local_dt, datetime):
            raise TypeError("local_dt 必须是 datetime")

        # 经度修正
        delta_minutes = (longitude - 120.0) * 4.0
        mean_solar_time = local_dt + timedelta(minutes=delta_minutes)

        # 方程时修正
        N = mean_solar_time.timetuple().tm_yday
        B = math.radians(360.0 / 365.0 * (N - 81))
        eot = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)

        true_dt = mean_solar_time + timedelta(minutes=eot)

        self.logger.info(
            "[TST] 真太阳时换算 | local='%s' | lng=%.6f | Δlon=%.2fmin | N=%d | EoT=%.2fmin | mean='%s' | true='%s'",
            local_dt.strftime("%Y-%m-%d %H:%M:%S"),
            longitude,
            delta_minutes,
            N,
            eot,
            mean_solar_time.strftime("%Y-%m-%d %H:%M:%S"),
            true_dt.strftime("%Y-%m-%d %H:%M:%S"),
        )
        return true_dt

    def _year_ganzhi(self, true_dt: datetime) -> Tuple[str, int, int, int]:
        """计算年柱"""
        y = true_dt.year
        approx_lichun = datetime(y, 2, 4)
        year_for_bazi = y - 1 if true_dt.date() < approx_lichun.date() else y
        gan_idx = (year_for_bazi - 4) % 10
        zhi_idx = (year_for_bazi - 4) % 12
        gz = TIANGAN[gan_idx] + DIZHI[zhi_idx]
        self.logger.info("[Y] 年柱 | year_for_bazi=%d | gan_idx=%d | zhi_idx=%d | gz=%s", year_for_bazi, gan_idx, zhi_idx, gz)
        return gz, year_for_bazi, gan_idx, zhi_idx

    def _month_index_by_terms(self, year_for_bazi: int, true_dt: datetime) -> int:
        """按节气计算月序"""
        terms: List[Tuple[date, str]] = []
        lichun = None
        for y in (year_for_bazi, year_for_bazi + 1):
            for fest in zh_solarterms:
                nm = fest.get_lang("zh")
                if nm == "立春":
                    lichun = fest(year_for_bazi) if y == year_for_bazi else lichun
                if nm in MAJOR_SOLAR_TERMS:
                    try:
                        d = fest(y)
                        terms.append((d, nm))
                    except Exception:
                        continue

        if lichun is None:
            lichun = date(year_for_bazi, 2, 4)

        terms = [t for t in terms if t[0] >= lichun]
        terms.sort(key=lambda x: x[0])

        if true_dt.date() < lichun:
            self.logger.info("[M] 月序 | true_dt<立春 → 12(腊月)")
            return 12

        month_idx = 1
        for d, _ in terms:
            if d <= true_dt.date():
                month_idx += 1
            else:
                break
        self.logger.info("[M] 月序 | month_index=%d", month_idx)
        return month_idx

    def _day_ganzhi(self, true_dt: datetime) -> Tuple[str, int]:
        """计算日柱"""
        ref_date = date(2000, 1, 1)
        ref_idx = 0
        for i in range(60):
            if TIANGAN[i % 10] == "戊" and DIZHI[i % 12] == "午":
                ref_idx = i
                break
        delta_days = (true_dt.date() - ref_date).days
        idx = (ref_idx + delta_days) % 60
        gan_idx = idx % 10
        zhi_idx = idx % 12
        gz = TIANGAN[gan_idx] + DIZHI[zhi_idx]
        self.logger.info(
            "[D] 日柱 | ref=%s(戊午,idx=%d) | Δdays=%d | idx=%d | gz=%s",
            ref_date.isoformat(),
            ref_idx,
            delta_days,
            idx,
            gz,
        )
        return gz, gan_idx

    def _hour_ganzhi(self, hour24: int, day_gan_idx: int) -> str:
        """计算时柱"""
        hour_branch_idx = ((hour24 + 1) // 2) % 12
        base = RAT_HOUR_STEM_MAP[day_gan_idx]
        gan = TIANGAN[(base + hour_branch_idx) % 10]
        zhi = DIZHI[hour_branch_idx]
        gz = gan + zhi
        self.logger.info("[H] 时柱 | hour=%02d | branch_idx=%d | day_gan_idx=%d | base=%d | gz=%s", hour24, hour_branch_idx, day_gan_idx, base, gz)
        return gz

    def calculate_bazi(self, true_dt: datetime) -> Dict[str, str]:
        """计算八字"""
        year_gz, year_for_bazi, year_gan_idx, _ = self._year_ganzhi(true_dt)
        month_index = self._month_index_by_terms(year_for_bazi, true_dt)
        first_month_stem_idx = FIRST_MONTH_STEM_MAP[year_gan_idx]
        month_gan_idx = (first_month_stem_idx + (month_index - 1)) % 10
        month_branch_idx = (2 + (month_index - 1)) % 12
        month_gz = TIANGAN[month_gan_idx] + DIZHI[month_branch_idx]
        self.logger.info(
            "[M] 月柱 | first_stem_idx=%d | gan_idx=%d | zhi_idx=%d | gz=%s",
            first_month_stem_idx,
            month_gan_idx,
            month_branch_idx,
            month_gz,
        )
        day_gz, day_gan_idx = self._day_ganzhi(true_dt)
        hour_gz = self._hour_ganzhi(true_dt.hour, day_gan_idx)
        return {"year": year_gz, "month": month_gz, "day": day_gz, "hour": hour_gz}

    def calculate_fortune(self, birth_true_dt: datetime, gender: str, month_gz: str, day_gz: str) -> Dict[str, object]:
        """计算大运"""
        prev_term, next_term = self.tool.nearest_major_terms_around(birth_true_dt)
        self.logger.info(
            "[LUCK] 节令邻近 | prev=%s | next=%s",
            prev_term.isoformat() if prev_term else None,
            next_term.isoformat() if next_term else None,
        )

        # 判断大运方向
        gender_str = (gender or "").strip().lower()
        is_male = gender_str in ("male", "男", "m")
        day_stem = day_gz[0]
        is_yang = day_stem in YANG_STEMS
        forward = (is_male and is_yang) or ((not is_male) and (not is_yang))
        direction_label = "顺行" if forward else "逆行"

        rule_text = f"{'男' if is_male else '女'}命 + {'阳干' if is_yang else '阴干'} → {direction_label}"
        self.logger.info("[LUCK] 起运方向 | %s", rule_text)

        # 计算起运时间
        target_term = next_term if forward else prev_term
        if target_term is None:
            target_term = next_term or prev_term or birth_true_dt

        delta_seconds = abs((target_term - birth_true_dt).total_seconds())
        delta_days = delta_seconds / 86400.0
        delta_hours = delta_seconds / 3600.0
        start_luck_age = max(delta_days / 3.0, 0.0)

        # 计算起运具体时间
        total_months = delta_days * 4.0
        months_int = int(total_months)
        years_part = months_int // 12
        months_part = months_int % 12
        remaining_days = (total_months - months_int) * 30.0
        start_luck_time = (
            birth_true_dt
            + relativedelta(years=years_part, months=months_part)
            + timedelta(days=remaining_days)
        )

        # 生成大运时间轴
        direction_step = 1 if forward else -1
        m_gan_idx = TIANGAN.index(month_gz[0])
        m_zhi_idx = DIZHI.index(month_gz[1])

        def fmt_age(val: float) -> str:
            formatted = f"{val:.2f}"
            return formatted.rstrip("0").rstrip(".")

        age_limit = 100.0
        timeline: List[Dict[str, object]] = []
        fortune_cycles: List[Dict[str, object]] = []
        cycle_num = 1

        while True:
            cycle_start_age = start_luck_age + (cycle_num - 1) * 10.0
            if cycle_start_age > age_limit:
                break
            cycle_end_age = min(cycle_start_age + 10.0, age_limit)
            offset = direction_step * cycle_num
            luck_gz = TIANGAN[(m_gan_idx + offset) % 10] + DIZHI[(m_zhi_idx + offset) % 12]
            fortune_cycles.append(
                {
                    "cycle_index": cycle_num,
                    "luck": luck_gz,
                    "start_age": round(cycle_start_age, 2),
                    "end_age": round(cycle_end_age, 2),
                    "period": f"{fmt_age(cycle_start_age)} ~ {fmt_age(cycle_end_age)} 岁",
                    "is_current": False,
                    "direction": direction_label,
                }
            )
            if cycle_end_age >= age_limit:
                break
            cycle_num += 1

        timeline.extend(fortune_cycles)

        # 确定当前大运
        now = datetime.now()
        current_age_years = max((now - birth_true_dt).total_seconds() / (365.2425 * 24 * 3600), 0.0)
        current_luck = "未起运"
        current_stage: Optional[Dict[str, object]] = None
        pre_luck_end = min(start_luck_age, age_limit)

        if now < start_luck_time or current_age_years < start_luck_age:
            if timeline:
                timeline[0]["is_current"] = False
            current_stage = {
                "cycle_index": 0,
                "luck": "未起运",
                "start_age": 0.0,
                "end_age": round(pre_luck_end, 2),
                "period": f"0 ~ {fmt_age(pre_luck_end)} 岁" if pre_luck_end > 0 else "0 岁",
                "is_current": True,
                "direction": direction_label,
            }
        else:
            if fortune_cycles:
                rd = relativedelta(now, start_luck_time)
                elapsed_years = rd.years + rd.months / 12.0 + rd.days / 365.2425
                cycle_index = int(elapsed_years // 10)
                cycle_index = max(0, min(cycle_index, len(fortune_cycles) - 1))
                fortune_cycles[cycle_index]["is_current"] = True
                current_stage = dict(fortune_cycles[cycle_index])
                current_luck = fortune_cycles[cycle_index]["luck"]

        if current_stage is None:
            current_stage = {
                "cycle_index": 1,
                "luck": fortune_cycles[0]["luck"] if fortune_cycles else current_luck,
                "start_age": fortune_cycles[0]["start_age"] if fortune_cycles else 0.0,
                "end_age": fortune_cycles[0]["end_age"] if fortune_cycles else 0.0,
                "period": fortune_cycles[0]["period"] if fortune_cycles else "0 岁",
                "is_current": True,
                "direction": direction_label,
            }
        else:
            current_stage["direction"] = direction_label

        self.logger.info(
            "[LUCK] 起运计算 | direction=%s | Δdays=%.4f | start_age=%.4f | start_time='%s' | current_luck=%s",
            direction_label,
            delta_days,
            start_luck_age,
            start_luck_time.strftime("%Y-%m-%d %H:%M:%S"),
            current_luck,
        )

        return {
            "start_luck_age": start_luck_age,
            "start_luck_time": start_luck_time,
            "direction": direction_label,
            "direction_forward": forward,
            "timeline": timeline,
            "current_luck": current_luck,
            "current_stage": current_stage,
            "calculation_notes": {
                "rule": rule_text,
                "target_term": target_term.strftime("%Y-%m-%d %H:%M:%S"),
                "delta_days": delta_days,
                "delta_hours": delta_hours,
                "start_luck_age": start_luck_age,
            },
        }


# ============================================================================
# 主Bazi类
# ============================================================================

class Bazi:
    """
    八字计算核心类
    
    功能：
    1. 八字计算（四柱干支）
    2. 真太阳时换算
    3. 大运推算
    4. 农历转换
    5. API接口封装
    """

    def __init__(self, gaode_api_key: Optional[str] = None, logger: Optional[logging.Logger] = None):
        """
        初始化Bazi类
        
        Args:
            gaode_api_key: 高德地图API密钥，默认从环境变量获取
            logger: 日志记录器，默认创建新的
        """
        self.gaode_api_key = gaode_api_key or os.getenv("GAODE_API_KEY", DEFAULT_GAODE_API_KEY)
        if not self.gaode_api_key:
            raise ValueError("未提供高德 Web 服务 KEY")
        
        self.logger = logger or self._create_logger()
        self.calculator = SolarTimeCalculator(self.gaode_api_key, self.logger)

    def _create_logger(self) -> logging.Logger:
        """创建日志记录器"""
        log = logging.getLogger("bazi.core")
        if getattr(log, "_configured", False):
            return log

        log.setLevel(logging.INFO)
        
        # 控制台输出
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        log.addHandler(console_handler)
        
        log.propagate = False
        setattr(log, "_configured", True)
        return log

    def validate_request(self, payload: Union[BaziRequestModel, Dict[str, Any]]) -> BaziRequestModel:
        """
        验证请求数据
        
        Args:
            payload: 请求数据
            
        Returns:
            验证后的请求模型
            
        Raises:
            ValueError: 数据验证失败
        """
        if isinstance(payload, BaziRequestModel):
            return payload
        
        try:
            return BaziRequestModel(**payload)
        except ValidationError as exc:
            error_msg = "; ".join(err["msg"] for err in exc.errors())
            raise ValueError(error_msg) from exc

    def compute_bazi(self, request: Union[BaziRequestModel, Dict[str, Any]]) -> Dict[str, object]:
        """
        计算八字
        
        Args:
            request: 八字计算请求
            
        Returns:
            八字计算结果
        """
        # 验证请求
        model = self.validate_request(request)
        
        # 创建调用ID
        call_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        adapter = CallIdAdapter(self.logger, {"call_id": call_id})
        
        adapter.info("==== BAZI JOB START ====")
        input_payload = {
            "birth_datetime": model.birth_datetime,
            "location_name": model.location_name,
            "gender": model.gender,
            "name": model.name,
        }
        adapter.info("请求参数: %s", json.dumps(input_payload, ensure_ascii=False))
        
        try:
            # 执行计算
            data = self._compute_core(model.birth_datetime, model.location_name, model.gender, adapter)
            
            # 计算年龄
            birth_date = datetime.strptime(data["true_solar_time"], "%Y-%m-%d %H:%M:%S").date()
            today = datetime.today().date()
            age = today.year - birth_date.year
            if (today.month, today.day) < (birth_date.month, birth_date.day):
                age -= 1
            
            # 构建响应
            output_payload = {
                "solar_datetime": data["birth_datetime_solar"],
                "true_solar_time": data["true_solar_time"],
                "lunar_date": data["birth_date_lunar"],
                "birth_time_hms": data["birth_time_hms"],
                "bazi": data["bazi"],
                "today_ganzhi": data["today_ganzhi"],
                "fortune": {
                    "fortune_direction": data["fortune_direction"],
                    "start_luck_age": data["start_luck_age"],
                    "start_luck_time": data["start_luck_time"],
                    "current_luck": data["current_luck"],
                    "current_fortune_stage": data["current_fortune_stage"],
                    "fortune_timeline": data["fortune_timeline"],
                    "fortune_calculation": data["fortune_calculation"],
                },
                "location": {
                    "longitude": data["longitude"],
                    "latitude": data["latitude"],
                },
                "meta": {
                    "age": age,
                    "name": model.name,
                    "gender": {
                        "code": data["gender"],
                        "label": data["gender_zh"],
                    },
                },
            }
            
            response_payload = {"input": input_payload, "output": output_payload}
            adapter.info("响应数据: %s", json.dumps(response_payload, ensure_ascii=False))
            
        except Exception:
            adapter.exception("执行失败")
            raise
        finally:
            adapter.info("==== BAZI JOB END ====")
        
        return response_payload

    def _compute_core(self, birth_datetime_str: str, location_name: str, gender: str, logger: logging.Logger) -> Dict[str, object]:
        """核心计算逻辑"""
        if not birth_datetime_str or not location_name or not gender:
            raise ValueError("缺少必要参数：birth_datetime | location_name | gender")

        try:
            birth_local_dt = datetime.strptime(birth_datetime_str, "%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            raise ValueError(f"出生时间格式错误，应为 'YYYY-MM-DD HH:MM:SS' | err={exc}")

        logger.info(
            "[ENTRY] 入参 | birth_local='%s' | loc='%s' | gender='%s'",
            birth_local_dt.strftime("%Y-%m-%d %H:%M:%S"),
            location_name,
            gender,
        )

        # 农历转换
        lunar_res = LunarCalendarTool().solar_to_lunar(birth_local_dt.year, birth_local_dt.month, birth_local_dt.day)
        birth_lunar_str = ""
        if lunar_res.status == 1 and lunar_res.lunar:
            birth_lunar_str = f"{lunar_res.lunar.year}年{'润' if lunar_res.lunar.isleap else ''}{lunar_res.lunar.month}月{lunar_res.lunar.day}日"
        else:
            logger.warning("[LUNAR] 公转农失败 | msg=%s", lunar_res.msg)

        # 获取坐标和真太阳时
        lng, lat = self.calculator.get_location_coordinates(location_name)
        true_dt = self.calculator.calculate_true_solar_time(birth_local_dt, lng)

        # 计算八字
        bazi = self.calculator.calculate_bazi(true_dt)

        # 计算大运
        fortune_info = self.calculator.calculate_fortune(true_dt, gender, bazi["month"], bazi["day"])

        # 计算今日干支
        today_gz = self.calculator.calculate_bazi(datetime.now())

        result = {
            "birth_datetime_solar": birth_local_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "birth_date_lunar": birth_lunar_str,
            "true_solar_time": true_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "birth_time_hms": birth_local_dt.strftime("%H:%M:%S"),
            "bazi": bazi,
            "start_luck_age": round(fortune_info["start_luck_age"], 4),
            "start_luck_time": fortune_info["start_luck_time"].strftime("%Y-%m-%d %H:%M:%S"),
            "current_luck": fortune_info["current_luck"],
            "today_ganzhi": today_gz,
            "longitude": lng,
            "latitude": lat,
            "gender": "male" if gender in ("男", "male", "M", "m") else "female",
            "gender_zh": "男" if gender in ("男", "male", "M", "m") else "女",
            "location_name": location_name,
            "fortune_direction": fortune_info["direction"],
            "fortune_timeline": fortune_info["timeline"],
            "current_fortune_stage": fortune_info["current_stage"],
            "fortune_calculation": {
                "rule": fortune_info["calculation_notes"]["rule"],
                "target_term": fortune_info["calculation_notes"]["target_term"],
                "delta_days": round(fortune_info["calculation_notes"]["delta_days"], 4),
                "delta_hours": round(fortune_info["calculation_notes"]["delta_hours"], 2),
                "start_luck_age": round(fortune_info["calculation_notes"]["start_luck_age"], 4),
            },
        }
        logger.info("[DONE] 计算完成")
        return result

    def get_bazi_simple(self, birth_datetime: str, location_name: str, gender: str, name: str = "") -> Dict[str, object]:
        """
        简化版八字计算接口
        
        Args:
            birth_datetime: 出生时间
            location_name: 出生地
            gender: 性别
            name: 姓名
            
        Returns:
            八字计算结果
        """
        request = {
            "birth_datetime": birth_datetime,
            "location_name": location_name,
            "gender": gender,
            "name": name or "未知"
        }
        return self.compute_bazi(request)

    def get_bazi_structured(self, request: Union[BaziRequestModel, Dict[str, Any]]) -> BaziResponseModel:
        """
        结构化八字计算接口
        
        Args:
            request: 八字计算请求
            
        Returns:
            结构化的八字响应模型
        """
        result = self.compute_bazi(request)
        return BaziResponseModel(**result)


# ============================================================================
# API接口封装
# ============================================================================

class BaziAPI:
    """八字计算API接口封装"""
    
    def __init__(self, bazi_instance: Optional[Bazi] = None):
        """
        初始化API接口
        
        Args:
            bazi_instance: Bazi实例，默认创建新的
        """
        self.bazi = bazi_instance or Bazi()
    
    def compute(self, payload: Union[BaziRequestModel, Dict[str, Any]]) -> BaziResponseModel:
        """
        计算八字API接口
        
        Args:
            payload: 请求数据
            
        Returns:
            八字计算结果
            
        Raises:
            ValueError: 请求数据错误
            Exception: 计算过程错误
        """
        try:
            return self.bazi.get_bazi_structured(payload)
        except ValueError as exc:
            raise ValueError(f"请求数据错误: {exc}") from exc
        except Exception as exc:
            self.bazi.logger.exception("八字计算失败")
            raise Exception(f"计算失败: {exc}") from exc
    
    def health_check(self) -> Dict[str, str]:
        """健康检查接口"""
        return {"status": "ok", "service": "bazi"}


# ============================================================================
# 便捷函数
# ============================================================================

def create_bazi_instance(gaode_api_key: Optional[str] = None) -> Bazi:
    """创建Bazi实例的便捷函数"""
    return Bazi(gaode_api_key=gaode_api_key)


def create_bazi_api(gaode_api_key: Optional[str] = None) -> BaziAPI:
    """创建BaziAPI实例的便捷函数"""
    bazi_instance = create_bazi_instance(gaode_api_key)
    return BaziAPI(bazi_instance)


# ============================================================================
# 示例用法
# ============================================================================

if __name__ == "__main__":
    # 示例1: 直接使用Bazi类
    print("=== 示例1: 直接使用Bazi类 ===")
    bazi = create_bazi_instance()
    
    request_data = {
        "birth_datetime": "1982-10-28 12:00:00",
        "location_name": "中国南宁市",
        "gender": "女",
        "name": "王鸥"
    }
    
    result = bazi.compute_bazi(request_data)
    print(f"八字: {result['output']['bazi']}")
    print(f"当前大运: {result['output']['fortune']['current_luck']}")
    
    # 示例2: 使用API接口
    print("\n=== 示例2: 使用API接口 ===")
    api = create_bazi_api()
    
    structured_result = api.compute(request_data)
    print(f"姓名: {structured_result.output.meta.name}")
    print(f"年龄: {structured_result.output.meta.age}")
    print(f"起运年龄: {structured_result.output.fortune.start_age}")
    
    # 示例3: 简化接口
    print("\n=== 示例3: 简化接口 ===")
    simple_result = bazi.get_bazi_simple(
        birth_datetime="1955-07-05 12:00:00",
        location_name="安徽省合肥市",
        gender="男",
        name="李克强"
    )
    print(f"八字: {simple_result['output']['bazi']}")
