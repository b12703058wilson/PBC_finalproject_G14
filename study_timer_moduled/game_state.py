# game_state.py — AppState、EXP/好感度計算、時間工具

import datetime
from dataclasses import dataclass, field

# ── 常數 ──────────────────────────────────────────────────────
DAILY_EXP_CAP     = 200   # 每日 EXP 上限
AFF_DECAY_PER_DAY = 5     # 每日好感度衰減基礎值
AFF_MIN, AFF_MAX  = 0, 100


# ── AppState ──────────────────────────────────────────────────
@dataclass
class AppState:
    # 使用者識別（duckdb 主鍵）
    user_id:        int   = None

    # 計時相關
    start_time:     float = None
    elapsed_time:   float = 0
    total_time:     float = 0
    average_time:   float = 0
    running:        bool  = False
    session_count:  int   = 0
    current_label:  str   = ""      # 本次計時使用的標籤

    # 使用者資料
    user_name:      str   = ""
    story_route:    str   = ""      # "romance" | "horror" | ""

    # 數值系統
    total_exp:      float = 0
    daily_exp:      float = 0
    affection:      float = 0
    daily_aff_gained: float = 0
    last_study_date: str  = ""
    today_chat_shown: bool = False

    # 劇情旗標
    story_flags:    dict  = field(default_factory=dict)

    # 標籤清單
    labels:         list  = field(default_factory=list)

    # 干擾計時追蹤
    # 當使用者因干擾暫停時，後台開始記錄干擾持續時間
    distraction_start:        float = None   # 干擾開始的 time.time()
    last_distraction_minutes: float = 0      # 上次干擾總分鐘數（用於下次開始時的提醒）
    last_distraction_reason:  str   = ""     # 上次干擾的主要原因

    # 番茄鐘設定
    pomodoro_work_minutes:    int   = 25     # 工作時間（分鐘）
    pomodoro_break_minutes:   int   = 5      # 休息時間（分鐘）


# ── EXP 計算 ──────────────────────────────────────────────────
def calc_exp(actual_secs: float, daily_exp_so_far: float = 0) -> float:
    """
    讀書 1 分鐘 = 1 EXP。
    當日累積 EXP 超過 120（2 小時）後，新獲得的 EXP × 1.2。
    每日上限 DAILY_EXP_CAP。
    """
    actual_min      = actual_secs / 60
    BONUS_THRESHOLD = 120   # 2 小時 = 120 EXP

    if daily_exp_so_far >= BONUS_THRESHOLD:
        raw_exp = actual_min * 1.2
    elif daily_exp_so_far + actual_min > BONUS_THRESHOLD:
        before  = BONUS_THRESHOLD - daily_exp_so_far
        after   = actual_min - before
        raw_exp = before + after * 1.2
    else:
        raw_exp = actual_min

    remaining_cap = max(0, DAILY_EXP_CAP - daily_exp_so_far)
    return min(raw_exp, remaining_cap)


# ── 好感度計算 ────────────────────────────────────────────────
def calc_affection_gain(actual_secs: float) -> float:
    """
    每 15 分鐘 +1 好感度。
    單次連續讀書超過 60 分鐘後，剩餘部分 × 2。
    """
    actual_min      = actual_secs / 60
    BONUS_THRESHOLD = 60

    if actual_min <= BONUS_THRESHOLD:
        return actual_min / 15
    else:
        before = BONUS_THRESHOLD / 15
        after  = (actual_min - BONUS_THRESHOLD) / 15 * 2
        return before + after


def calc_affection_decay(days_absent: int) -> float:
    return AFF_DECAY_PER_DAY * min(days_absent, 4)


# ── 時間工具 ──────────────────────────────────────────────────
def fmt(secs: float) -> str:
    """秒數 → HH:MM:SS"""
    secs = max(0, int(secs))
    return f"{secs//3600:02}:{(secs%3600)//60:02}:{secs%60:02}"

def fmt_min(secs: float) -> str:
    """秒數 → MM:SS"""
    secs = max(0, int(secs))
    return f"{secs//60:02}:{secs%60:02}"

def time_str_to_sec(ts: str) -> int:
    h, m, s = map(int, ts.split(":"))
    return h * 3600 + m * 60 + s

def time_str_to_min(ts: str) -> float:
    h, m, s = map(int, ts.split(":"))
    return h * 60 + m + s / 60

def today_str() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")


# ── 每日衰減（登入時執行）────────────────────────────────────
def apply_daily_decay(state: AppState) -> float:
    """回傳實際衰減量，並更新 state.affection。"""
    today = today_str()
    if state.last_study_date != today:
        state.daily_exp       = 0
        state.daily_aff_gained = 0
        state.today_chat_shown = False
    if not state.last_study_date or state.last_study_date == today:
        return 0.0
    last        = datetime.date.fromisoformat(state.last_study_date)
    days_absent = (datetime.date.today() - last).days - 1
    if days_absent <= 0:
        return 0.0
    decay           = calc_affection_decay(days_absent)
    state.affection = max(AFF_MIN, state.affection - decay)
    return decay
