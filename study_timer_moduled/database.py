# database.py — 薄薄的相容層
# 原本散落各頁面的 database.* 呼叫，全部轉接到 data_bridge.py
# 舊的函式簽章保持不變，讓 timer_page / route_page / main.py 不需要大改

from data_bridge import (
    init_db,
    load_user_data,
    save_session        as _db_save_session,
    save_story_flag     as _db_save_flag,
    save_user_name      as _db_save_name,
    save_story_route    as _db_save_route,
    save_today_chat_shown as _db_save_chat,
    save_labels         as _db_save_labels,
    get_labels,
    get_dashboard_stats,
)


# ── 初始化（對應舊的 init_excel）────────────────────────────
def init_db_compat(story_prologue: dict, stories: dict):
    """首次啟動時建立資料庫結構。story_prologue / stories 參數保留相容，不使用。"""
    init_db()


# ── 載入資料（對應舊的 load_excel_data）─────────────────────
def load_db_data(user_id: int, story_prologue: dict, stories: dict) -> dict:
    return load_user_data(user_id, story_prologue, stories)


# ── 計時儲存（對應舊的 save_session）────────────────────────
def save_session(game_data_or_uid, state, elapsed_time: float, label: str = ""):
    """
    相容舊簽章：第一個參數舊版傳 game_data（str），現在傳 user_id（int）。
    timer_page 已更新為傳 state.user_id，但若傳入字串也安全地忽略。
    """
    uid = state.user_id if hasattr(state, 'user_id') else None
    if uid is None:
        return
    _db_save_session(uid, state, elapsed_time, label)


# ── 劇情旗標（對應舊的 save_story_flag）─────────────────────
def save_story_flag(game_data_or_uid, flag_key: str, value: bool, user_id: int = None):
    """
    舊版：save_story_flag(game_data, excel_cell, True)
    新版：cell 已改為 story_id（flag_key），第一個參數忽略，用 user_id。
    timer_page 現在直接傳 state.user_id 作第一參數。
    """
    uid = game_data_or_uid if isinstance(game_data_or_uid, int) else user_id
    if uid is None:
        return
    _db_save_flag(uid, flag_key, value)


# ── 使用者名稱 ──────────────────────────────────────────────
def save_user_name(game_data_or_uid, name: str):
    uid = game_data_or_uid if isinstance(game_data_or_uid, int) else None
    if uid is None:
        return
    _db_save_name(uid, name)


# ── 故事路線 ─────────────────────────────────────────────────
def save_story_route(game_data_or_uid, route: str):
    uid = game_data_or_uid if isinstance(game_data_or_uid, int) else None
    if uid is None:
        return
    _db_save_route(uid, route)


# ── 今日日常已顯示 ───────────────────────────────────────────
def save_today_chat_shown(game_data_or_uid):
    uid = game_data_or_uid if isinstance(game_data_or_uid, int) else None
    if uid is None:
        return
    _db_save_chat(uid)


# ── 標籤管理 ─────────────────────────────────────────────────
def save_labels(game_data_or_uid, labels: list):
    uid = game_data_or_uid if isinstance(game_data_or_uid, int) else None
    if uid is None:
        return
    _db_save_labels(uid, labels)

def add_label(user_id: int, name: str, color: str = "#D4537E"):
    from data_bridge import get_connection
    con = get_connection()
    try:
        con.sql("""
            INSERT INTO labels (user_id, name, color)
            VALUES ($uid, $name, $color)
        """, params={'uid': user_id, 'name': name, 'color': color})
    finally:
        con.close()


# ── 統計頁輔助（stat_page 使用）─────────────────────────────
def load_session_history(game_data_or_uid) -> list:
    """回傳空清單：stat_page 已改用 get_dashboard_stats，此函式僅保留相容。"""
    return []


def load_label_stats(game_data_or_uid) -> dict:
    """回傳空字典：stat_page 已改用 get_dashboard_stats。"""
    return {}
