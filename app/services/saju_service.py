from lunar_python import Lunar, Solar

STEM_ELEMENTS = dict(zip("甲乙丙丁戊己庚辛壬癸", ["wood","wood","fire","fire","earth","earth","metal","metal","water","water"]))
BRANCH_ELEMENTS = dict(zip("寅卯巳午辰戌丑未申酉亥子", ["wood","wood","fire","fire","earth","earth","earth","earth","metal","metal","water","water"]))
HANJA_TO_KO = str.maketrans("甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥", "갑을병정무기경신임계자축인묘진사오미신유술해")
KO = {"wood":"목","fire":"화","earth":"토","metal":"금","water":"수"}
DAY_MASTER_PLAIN = {
    "갑": "큰 나무처럼 방향을 정하면 꾸준히 성장하려는 편",
    "을": "주변과 조화를 이루며 유연하게 길을 찾는 편",
    "병": "밝고 적극적으로 자신의 생각을 표현하는 편",
    "정": "세심하고 따뜻하게 사람과 상황을 살피는 편",
    "무": "쉽게 흔들리지 않고 책임감 있게 버티는 편",
    "기": "현실을 꼼꼼히 돌보고 필요한 것을 채워가는 편",
    "경": "기준이 분명하고 결정을 행동으로 옮기는 편",
    "신": "완성도와 예의를 중시하며 섬세하게 판단하는 편",
    "임": "큰 흐름을 읽고 변화에 맞춰 움직이는 편",
    "계": "감수성이 풍부하고 작은 변화도 빠르게 알아차리는 편",
}
ELEMENT_PLAIN = {
    "wood": ("성장하고 새롭게 시도하는 힘", "계획을 실제 시작으로 옮기는 연습"),
    "fire": ("감정과 의사를 밖으로 표현하는 힘", "마음을 분명하게 표현하는 연습"),
    "earth": ("안정감을 만들고 꾸준히 유지하는 힘", "변화도 안전하게 받아들이는 연습"),
    "metal": ("기준을 세우고 정리·판단하는 힘", "우선순위를 분명히 정하는 연습"),
    "water": ("상황을 관찰하고 유연하게 대응하는 힘", "서두르지 않고 충분히 살피는 연습"),
}

def _element_counts(pillars: list[str]) -> dict[str, int]:
    counts = {key: 0 for key in KO}
    for pillar in pillars:
        counts[STEM_ELEMENTS[pillar[0]]] += 1
        counts[BRANCH_ELEMENTS[pillar[1]]] += 1
    return counts

def calculate_saju(profile, target_year: int, target_month: int) -> dict:
    """절기 기준 팔자·오행·십성을 계산한다. 출생 지역 진태양시 보정은 별도 전문 영역이다."""
    birth = profile.birth_date
    hour, minute = (12, 0) if profile.time_unknown or not profile.birth_time else map(int, profile.birth_time.split(":"))
    if profile.calendar_type == "lunar":
        lunar = Lunar.fromYmdHms(birth.year, birth.month, birth.day, hour, minute, 0)
        solar = lunar.getSolar()
    else:
        solar = Solar.fromYmdHms(birth.year, birth.month, birth.day, hour, minute, 0)
        lunar = solar.getLunar()
    eight = lunar.getEightChar()
    pillar_values = [eight.getYear(), eight.getMonth(), eight.getDay(), eight.getTime()]
    pillars = dict(zip(["year", "month", "day", "hour"], [value.translate(HANJA_TO_KO) for value in pillar_values]))
    counts = _element_counts(pillar_values)
    strong = max(counts, key=counts.get)
    weak = min(counts, key=counts.get)
    day_master = eight.getDayGan().translate(HANJA_TO_KO)
    target = Solar.fromYmdHms(target_year, target_month, 15, 12, 0, 0).getLunar()
    ten_gods = [eight.getYearShiShenGan(), eight.getMonthShiShenGan(), "일주", eight.getTimeShiShenGan()]
    strength_plain = ELEMENT_PLAIN[strong][0]
    balance_plain = ELEMENT_PLAIN[weak][1]
    plain_summary = (f"기본적으로 {DAY_MASTER_PLAIN[day_master]}입니다. "
                     f"현재 구성에서는 {strength_plain}이 비교적 자연스러운 강점으로 나타납니다. "
                     f"한쪽으로 치우치지 않으려면 {balance_plain}을 의식하면 좋습니다.")
    return {
        "calculation_mode": "lunar_python_eight_char",
        "solar_birth": f"{solar.getYear():04d}-{solar.getMonth():02d}-{solar.getDay():02d}",
        "lunar_birth": f"{lunar.getYear():04d}-{abs(lunar.getMonth()):02d}-{lunar.getDay():02d}",
        "four_pillars": pillars,
        "day_master": day_master,
        "five_elements": counts,
        "ten_gods": ten_gods,
        "strength": f"겉으로 드러난 8글자를 단순 집계하면 {KO[strong]} 요소가 상대적으로 많음",
        "useful_elements": [],
        "unfavorable_elements": [],
        "professional_useful_element_calculated": False,
        "major_luck": [],
        "year_luck": {"year": target_year, "gan_zhi": target.getYearInGanZhiExact().translate(HANJA_TO_KO)},
        "month_luck": {"month": target_month, "gan_zhi": target.getMonthInGanZhiExact().translate(HANJA_TO_KO)},
        "summary": plain_summary,
        "plain_language": {"personality": DAY_MASTER_PLAIN[day_master], "natural_strength": strength_plain,
                           "balance_tip": balance_plain},
        "technical_summary": f"년주 {pillars['year']}, 월주 {pillars['month']}, 일주 {pillars['day']}, 시주 {pillars['hour']}, 일간 {day_master}. 오행상 {KO[strong]}가 상대적으로 많고 {KO[weak]}가 적습니다.",
        "calculation_basis": {
            "engine": "lunar_python",
            "calendar_rule": "입력 달력을 양력·음력으로 변환한 뒤 절기 기준 연주·월주를 계산",
            "time_basis": "출생 시간 미상으로 12:00 가정" if profile.time_unknown or not profile.birth_time else f"입력 시각 {hour:02d}:{minute:02d}을 표준시 그대로 사용",
            "region_correction": "미적용 (출생 지역은 기록용)",
            "element_method": "천간·지지 8글자의 겉오행 단순 개수",
            "gender_usage": "원국 네 기둥 계산에는 사용하지 않음; 대운 계산은 현재 미구현",
        },
        "confidence": {
            "pillars": "검증 가능한 달력 라이브러리 계산값",
            "interpretation": "MVP 자기성찰용 참고 해석",
        },
        "notice": "절기 기준 원국 계산입니다. 지역별 진태양시, 대운, 지장간·계절 세력, 전문 용신 판정은 포함하지 않습니다. 절입일이나 시각 경계에 가까우면 전문 만세력과 결과가 다를 수 있습니다."
    }
