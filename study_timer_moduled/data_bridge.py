# data_bridge.py — DuckDB 資料存取層
# 整合自組員的 tables_and_databridge.py
# 所有 DB 操作都集中在此，其他模組只需 import 這裡的函式

import duckdb
from datetime import datetime, timedelta
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'study_app.db')


# ══════════════════════════════════════════════════════════════
# 連線
# ══════════════════════════════════════════════════════════════

def get_connection():
    return duckdb.connect(DB_PATH)


# ══════════════════════════════════════════════════════════════
# 初始化資料庫（首次啟動時建立所有表格）
# ══════════════════════════════════════════════════════════════

def init_db():
    con = duckdb.connect(DB_PATH)
    try:
        con.sql("CREATE SEQUENCE IF NOT EXISTS seq_users        START 1;")
        con.sql("CREATE SEQUENCE IF NOT EXISTS seq_labels       START 1;")
        con.sql("CREATE SEQUENCE IF NOT EXISTS seq_sessions     START 1;")
        con.sql("CREATE SEQUENCE IF NOT EXISTS seq_distractions START 1;")
        con.sql("CREATE SEQUENCE IF NOT EXISTS seq_story_progress START 1;")

        con.sql("""
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY DEFAULT nextval('seq_users'),
                username        TEXT UNIQUE,
                exp             FLOAT     DEFAULT 0,
                daily_exp       FLOAT     DEFAULT 0,
                affection       FLOAT     DEFAULT 0,
                daily_aff_gained FLOAT    DEFAULT 0,
                total_hours     FLOAT     DEFAULT 0,   -- 累積秒數
                last_session_id INTEGER   DEFAULT NULL,
                last_study_date TEXT      DEFAULT '',  -- YYYY-MM-DD
                today_chat_shown INTEGER  DEFAULT 0,
                story_route     TEXT      DEFAULT '',
                last_study_time TIMESTAMP DEFAULT NULL
            )
        """)

        con.sql("""
            CREATE TABLE IF NOT EXISTS labels (
                id      INTEGER PRIMARY KEY DEFAULT nextval('seq_labels'),
                user_id INTEGER,
                name    TEXT,
                color   TEXT DEFAULT '#D4537E'
            )
        """)

        con.sql("""
            CREATE TABLE IF NOT EXISTS distraction_types (
                id   INTEGER PRIMARY KEY,
                name TEXT
            )
        """)

        con.sql("""
            CREATE TABLE IF NOT EXISTS sessions (
                id                      INTEGER PRIMARY KEY DEFAULT nextval('seq_sessions'),
                user_id                 INTEGER,
                label_id                INTEGER,
                mode                    TEXT,
                target_duration         INTEGER DEFAULT 0,
                start_time              TIMESTAMP,
                end_time                TIMESTAMP,
                actual_duration         INTEGER,   -- 秒數
                total_distraction_count INTEGER DEFAULT 0,
                total_distraction_time  INTEGER DEFAULT 0
            )
        """)

        con.sql("""
            CREATE TABLE IF NOT EXISTS distractions (
                id          INTEGER PRIMARY KEY DEFAULT nextval('seq_distractions'),
                session_id  INTEGER,
                type_id     INTEGER,
                start_time  TIMESTAMP,
                end_time    TIMESTAMP,
                duration    INTEGER,
                is_overtime BOOLEAN DEFAULT FALSE,
                is_reminded BOOLEAN DEFAULT FALSE
            )
        """)

        con.sql("""
            CREATE TABLE IF NOT EXISTS story_flags (
                user_id  INTEGER,
                flag_key TEXT,
                value    INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, flag_key)
            )
        """)

        con.sql("""
            INSERT INTO distraction_types (id, name)
            VALUES
                (1, '去廁所'),
                (2, '重要訊息'),
                (3, '吃東西'),
                (4, '突發事情'),
                (5, '聊天'),
                (6, '其他')
            ON CONFLICT (id) DO NOTHING
        """)
    finally:
        con.close()


# ══════════════════════════════════════════════════════════════
# 使用者：登入 / 建立
# ══════════════════════════════════════════════════════════════

def get_or_create_user(username: str) -> int:
    """
    依名稱取得 user_id；若不存在則自動建立。
    回傳 user_id。
    """
    con = get_connection()
    try:
        row = con.sql(
            "SELECT id FROM users WHERE username = $name",
            params={'name': username}
        ).fetchone()
        if row:
            return row[0]

        con.sql(
            "INSERT INTO users (username) VALUES ($name)",
            params={'name': username}
        )
        user_id = con.sql(
            "SELECT id FROM users WHERE username = $name",
            params={'name': username}
        ).fetchone()[0]
        return user_id
    finally:
        con.close()


def get_user_by_name(username: str) -> int | None:
    con = get_connection()
    try:
        row = con.sql(
            "SELECT id FROM users WHERE username = $name",
            params={'name': username}
        ).fetchone()
        return row[0] if row else None
    finally:
        con.close()


# ══════════════════════════════════════════════════════════════
# 載入全部遊戲狀態
# ══════════════════════════════════════════════════════════════

def load_user_data(user_id: int, story_prologue: dict, stories: dict) -> dict:
    """
    對應舊的 load_excel_data()，一次讀取所有遊戲狀態。
    """
    con = get_connection()
    try:
        # 蒐集所有劇情 flag key
        all_flag_keys = [story_prologue["id"]]
        for route_stories in stories.values():
            for s in route_stories:
                all_flag_keys.append(s["id"])
                for b in s.get("branches", []):
                    all_flag_keys.append(b["id"])

        result = {
            "total_time": 0, "session_count": 0, "average_time": 0,
            "user_name": "", "story_route": "",
            "story_flags": {k: False for k in all_flag_keys},
            "total_exp": 0, "daily_exp": 0, "affection": 0,
            "daily_aff_gained": 0, "last_study_date": "",
            "today_chat_shown": False, "labels": [],
        }

        # ── 使用者基本資料 ──
        row = con.sql("""
            SELECT username, exp, daily_exp, affection, daily_aff_gained,
                   total_hours, last_study_date, today_chat_shown, story_route
            FROM users WHERE id = $uid
        """, params={'uid': user_id}).fetchone()

        if row:
            result["user_name"]        = row[0] or ""
            result["total_exp"]        = row[1] or 0
            result["daily_exp"]        = row[2] or 0
            result["affection"]        = row[3] or 0
            result["daily_aff_gained"] = row[4] or 0
            result["total_time"]       = row[5] or 0   # 以秒為單位
            result["last_study_date"]  = row[6] or ""
            result["today_chat_shown"] = bool(row[7])
            result["story_route"]      = row[8] or ""

        # ── session 計數 & 平均 ──
        stats = con.sql("""
            SELECT COUNT(*), AVG(actual_duration)
            FROM sessions WHERE user_id = $uid
        """, params={'uid': user_id}).fetchone()
        if stats and stats[0]:
            result["session_count"] = int(stats[0])
            result["average_time"]  = float(stats[1] or 0)

        # ── 劇情旗標 ──
        flags = con.sql("""
            SELECT flag_key, value FROM story_flags WHERE user_id = $uid
        """, params={'uid': user_id}).fetchall()
        for key, val in flags:
            if key in result["story_flags"]:
                result["story_flags"][key] = bool(val)

        # ── 標籤清單 ──
        labels_rows = con.sql("""
            SELECT name, color FROM labels WHERE user_id = $uid ORDER BY id
        """, params={'uid': user_id}).fetchall()
        result["labels"] = [{"name": r[0], "color": r[1]} for r in labels_rows]

        return result
    finally:
        con.close()


# ══════════════════════════════════════════════════════════════
# 儲存計時紀錄
# ══════════════════════════════════════════════════════════════

def save_session(user_id: int, state, elapsed_secs: float, label_name: str = ""):
    """
    對應舊的 save_session()，暫停時呼叫。
    """
    con = get_connection()
    try:
        # 解析標籤 id
        label_id = None
        if label_name:
            row = con.sql(
                "SELECT id FROM labels WHERE user_id=$uid AND name=$n",
                params={'uid': user_id, 'n': label_name}
            ).fetchone()
            if row:
                label_id = row[0]

        now        = datetime.now()
        start_time = datetime.fromtimestamp(
            now.timestamp() - elapsed_secs
        )

        # 計算干擾統計
        dist_count = len([d for d in getattr(state, 'current_distractions', [])
                          if d.get('is_distraction', True)])
        dist_secs  = int(getattr(state, 'distraction_pause_seconds', 0))

        mode = "番茄鐘" if getattr(state, 'pomodoro_mode', False) else "自訂"

        con.sql("""
            INSERT INTO sessions (
                user_id, label_id, mode, target_duration,
                start_time, end_time, actual_duration,
                total_distraction_count, total_distraction_time
            ) VALUES (
                $uid, $lid, $mode, 0,
                $st, $et, $dur,
                $dcnt, $dtime
            )
        """, params={
            'uid' : user_id, 'lid': label_id, 'mode': mode,
            'st'  : start_time, 'et': now,
            'dur' : int(elapsed_secs),
            'dcnt': dist_count, 'dtime': dist_secs
        })

        session_id = con.sql("SELECT MAX(id) FROM sessions").fetchone()[0]

        # 更新使用者累積資料
        con.sql("""
            UPDATE users SET
                exp              = $exp,
                daily_exp        = $dexp,
                affection        = $aff,
                daily_aff_gained = $daff,
                total_hours      = $total,
                last_study_date  = $lsd,
                last_study_time  = $now,
                today_chat_shown = $tcs,
                last_session_id  = $sid,
                story_route      = $route
            WHERE id = $uid
        """, params={
            'exp'  : round(state.total_exp, 2),
            'dexp' : round(state.daily_exp, 2),
            'aff'  : round(state.affection, 2),
            'daff' : round(state.daily_aff_gained, 2),
            'total': state.total_time,
            'lsd'  : state.last_study_date,
            'now'  : now,
            'tcs'  : 1 if state.today_chat_shown else 0,
            'sid'  : session_id,
            'route': state.story_route,
            'uid'  : user_id,
        })

        return session_id
    finally:
        con.close()


# ══════════════════════════════════════════════════════════════
# 劇情旗標
# ══════════════════════════════════════════════════════════════

def save_story_flag(user_id: int, flag_key: str, value: bool):
    """對應舊的 save_story_flag()，cell 改為 flag_key（story id）。"""
    con = get_connection()
    try:
        con.sql("""
            INSERT INTO story_flags (user_id, flag_key, value)
            VALUES ($uid, $key, $val)
            ON CONFLICT (user_id, flag_key) DO UPDATE SET value = $val
        """, params={'uid': user_id, 'key': flag_key, 'val': 1 if value else 0})
    finally:
        con.close()


# ══════════════════════════════════════════════════════════════
# 使用者基本資料更新
# ══════════════════════════════════════════════════════════════

def save_user_name(user_id: int, name: str):
    con = get_connection()
    try:
        con.sql("UPDATE users SET username=$n WHERE id=$uid",
                params={'n': name, 'uid': user_id})
    finally:
        con.close()


def save_story_route(user_id: int, route: str):
    con = get_connection()
    try:
        con.sql("UPDATE users SET story_route=$r WHERE id=$uid",
                params={'r': route, 'uid': user_id})
    finally:
        con.close()


def save_today_chat_shown(user_id: int):
    con = get_connection()
    try:
        con.sql("UPDATE users SET today_chat_shown=1 WHERE id=$uid",
                params={'uid': user_id})
    finally:
        con.close()


# ══════════════════════════════════════════════════════════════
# 標籤管理
# ══════════════════════════════════════════════════════════════

def save_labels(user_id: int, labels: list):
    """對應舊的 save_labels()，整份清單同步到 DB。"""
    con = get_connection()
    try:
        existing = {
            row[1]: row[0]
            for row in con.sql(
                "SELECT id, name FROM labels WHERE user_id=$uid",
                params={'uid': user_id}
            ).fetchall()
        }
        new_names = {l["name"] for l in labels}

        # 刪除已移除的標籤
        for name, lid in existing.items():
            if name not in new_names:
                con.sql(
                    "UPDATE sessions SET label_id=NULL WHERE user_id=$uid AND label_id=$lid",
                    params={'uid': user_id, 'lid': lid}
                )
                con.sql(
                    "DELETE FROM labels WHERE id=$lid",
                    params={'lid': lid}
                )

        # 新增不存在的標籤
        for lbl in labels:
            if lbl["name"] not in existing:
                con.sql(
                    "INSERT INTO labels (user_id, name, color) VALUES ($uid,$n,$c)",
                    params={'uid': user_id, 'n': lbl["name"], 'c': lbl.get("color", "#D4537E")}
                )
    finally:
        con.close()


def get_labels(user_id: int) -> list:
    """回傳 [{'id':..., 'name':..., 'color':...}, ...]"""
    con = get_connection()
    try:
        rows = con.sql(
            "SELECT id, name, color FROM labels WHERE user_id=$uid ORDER BY id",
            params={'uid': user_id}
        ).fetchall()
        return [{"id": r[0], "name": r[1], "color": r[2]} for r in rows]
    finally:
        con.close()


# ══════════════════════════════════════════════════════════════
# 統計頁資料
# ══════════════════════════════════════════════════════════════

def get_dashboard_stats(user_id: int, days: int = 30) -> dict:
    """
    一次取回統計頁所需的所有數據。
    days: 趨勢圖 / 干擾圖的時間範圍（核心數字不受限）
    """
    con = get_connection()
    try:
        days = max(1, int(days))
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        # ① 核心數字（全部累積，不受天數限制）
        user_row = con.sql("""
            SELECT exp, daily_exp, affection, total_hours
            FROM users WHERE id=$uid
        """, params={'uid': user_id}).fetchone()

        sess_stats = con.sql("""
            SELECT
                COUNT(id),
                AVG(actual_duration),
                MAX(actual_duration),
                SUM(CASE WHEN total_distraction_count=0 THEN 1 ELSE 0 END),
                SUM(total_distraction_count)
            FROM sessions
            WHERE user_id=$uid AND start_time >= CAST($cut AS TIMESTAMP)
        """, params={'uid': user_id, 'cut': cutoff}).fetchone()

        # ② 各標籤時間分布（圓餅圖）
        pie_df = con.sql("""
            SELECT
                COALESCE(l.name, '未分類') AS label_name,
                SUM(s.actual_duration)     AS total_duration
            FROM sessions s
            LEFT JOIN labels l ON s.label_id = l.id
            WHERE s.user_id=$uid AND s.start_time >= CAST($cut AS TIMESTAMP)
            GROUP BY label_name
            ORDER BY total_duration DESC
        """, params={'uid': user_id, 'cut': cutoff}).df()

        # ③ 每日讀書趨勢（長條圖）
        bar_df = con.sql("""
            SELECT
                CAST(start_time AS DATE) AS study_date,
                SUM(actual_duration)     AS daily_seconds
            FROM sessions
            WHERE user_id=$uid AND start_time >= CAST($cut AS TIMESTAMP)
            GROUP BY CAST(start_time AS DATE)
            ORDER BY study_date ASC
        """, params={'uid': user_id, 'cut': cutoff}).df()

        if not bar_df.empty:
            bar_df['study_date'] = bar_df['study_date'].astype(str)

        # ④ 干擾類型統計
        dist_df = con.sql("""
            SELECT
                dt.name         AS type_name,
                COUNT(d.id)     AS count,
                SUM(d.duration) AS total_duration
            FROM distractions d
            JOIN distraction_types dt ON d.type_id    = dt.id
            JOIN sessions           s ON d.session_id = s.id
            WHERE s.user_id=$uid AND s.start_time >= CAST($cut AS TIMESTAMP)
            GROUP BY dt.name
            ORDER BY total_duration DESC
        """, params={'uid': user_id, 'cut': cutoff}).df()

        # ⑤ 最近 5 筆 session（長條趨勢用）
        recent_df = con.sql("""
            SELECT actual_duration, start_time
            FROM sessions
            WHERE user_id=$uid
            ORDER BY start_time DESC
            LIMIT 5
        """, params={'uid': user_id}).df()
        if not recent_df.empty:
            recent_df = recent_df.iloc[::-1].reset_index(drop=True)

        u = user_row or (0, 0, 0, 0)
        s = sess_stats or (0, 0, 0, 0, 0)
        return {
            "core_stats": {
                "total_exp"              : u[0] or 0,
                "daily_exp"              : u[1] or 0,
                "affection"              : u[2] or 0,
                "total_hours"            : u[3] or 0,   # 秒
                "session_count"          : int(s[0] or 0),
                "avg_duration"           : float(s[1] or 0),   # 秒
                "max_duration"           : int(s[2] or 0),     # 秒
                "perfect_sessions"       : int(s[3] or 0),
                "total_distraction_count": int(s[4] or 0),
            },
            "pie_chart"        : pie_df.to_dict(orient='records'),
            "bar_chart"        : bar_df.to_dict(orient='records'),
            "distraction_chart": dist_df.to_dict(orient='records'),
            "recent_sessions"  : recent_df.to_dict(orient='records'),
        }
    finally:
        con.close()


# ══════════════════════════════════════════════════════════════
# 干擾提醒（開始讀書前呼叫）
# ══════════════════════════════════════════════════════════════

def check_overtime_reminder(user_id: int):
    con = get_connection()
    try:
        result = con.sql("""
            SELECT d.id, dt.name, d.duration
            FROM distractions d
            JOIN distraction_types dt ON d.type_id    = dt.id
            JOIN sessions           s  ON d.session_id = s.id
            WHERE s.user_id=    $uid
              AND d.is_overtime = TRUE
              AND d.is_reminded = FALSE
        """, params={'uid': user_id}).df()

        if len(result) > 0:
            con.sql("""
                UPDATE distractions
                SET is_reminded = TRUE
                WHERE is_overtime = TRUE AND is_reminded = FALSE
                  AND session_id IN (SELECT id FROM sessions WHERE user_id=$uid)
            """, params={'uid': user_id})

        return result
    finally:
        con.close()


# ══════════════════════════════════════════════════════════════
# 相容 stub（給 plot_manager.py 用，stat_page 不直接呼叫）
# ══════════════════════════════════════════════════════════════

def get_recent_sessions(user_id: int, limit: int = 5):
    con = get_connection()
    try:
        df = con.sql("""
            SELECT actual_duration, start_time
            FROM sessions WHERE user_id=$uid
            ORDER BY start_time DESC LIMIT $lim
        """, params={'uid': user_id, 'lim': limit}).df()
        if not df.empty:
            df['start_time'] = df['start_time'].astype('datetime64[ns]')
        return df
    finally:
        con.close()


def get_label_summary(user_id: int):
    con = get_connection()
    try:
        return con.sql("""
            SELECT COALESCE(l.name,'未分類') AS label_name,
                   SUM(s.actual_duration)   AS total_duration
            FROM sessions s LEFT JOIN labels l ON s.label_id=l.id
            WHERE s.user_id=$uid
            GROUP BY label_name ORDER BY total_duration DESC
        """, params={'uid': user_id}).df()
    finally:
        con.close()


def get_distraction_summary(user_id: int):
    con = get_connection()
    try:
        return con.sql("""
            SELECT dt.name AS type_name, SUM(d.duration) AS total_duration
            FROM distractions d
            JOIN distraction_types dt ON d.type_id=dt.id
            JOIN sessions s ON d.session_id=s.id
            WHERE s.user_id=$uid
            GROUP BY dt.name ORDER BY total_duration DESC
        """, params={'uid': user_id}).df()
    finally:
        con.close()
