import duckdb
from datetime import datetime

# ==============================
# 建立資料庫連線的函式
# 每次需要連線時呼叫，用完透過 finally 自動關閉
# ==============================
def get_connection():
    return duckdb.connect('study_app.db')


# ==============================================================
# 【使用者註冊】
# ==============================================================

def register_user(username):
    """
    註冊新使用者
    註冊成功後自動建立劇情進度

    參數：
        username : 使用者輸入的名字
    回傳：
        成功回傳新的 user_id，名稱重複回傳 None
    """
    con = get_connection()
    try:
        # 新增使用者，username 重複會拋出例外
        con.sql(
            "INSERT INTO users (username) VALUES ($name)",
            params={'name': username}
        )

        # 撈回剛剛產生的 user_id
        user_id = con.sql(
            "SELECT id FROM users WHERE username = $name",
            params={'name': username}
        ).fetchone()[0]

        # 自動幫新使用者建立預設劇情進度
        con.sql("""
            INSERT INTO story_progress (user_id, story_id, chapter, branch)
            VALUES ($user_id, 1, 0, NULL)
        """, params={'user_id': user_id})

        return user_id

    except Exception as e:
        print(f"註冊失敗：名稱已存在或發生錯誤 - {e}")
        return None
    finally:
        con.close()


def get_user_id(username):
    """
    透過使用者名稱查詢 user_id
    用於舊使用者重新登入時

    參數：
        username : 使用者名稱
    回傳：
        user_id（找不到回傳 None）
    """
    con = get_connection()
    try:
        result = con.sql(
            "SELECT id FROM users WHERE username = $name",
            params={'name': username}
        ).fetchone()
        return result[0] if result else None
    finally:
        con.close()


# ==============================================================
# 【給計時組用】
# ==============================================================

def save_session(user_id, label_id, mode, target_duration,
                 start_time, end_time,
                 total_distraction_count, total_distraction_time):
    """
    讀書結束後，存一筆完整的讀書紀錄進資料庫
    同時更新使用者的累積時數和上次讀書時間

    參數：
        user_id                 : 使用者編號
        label_id                : 讀書標籤編號（對應 labels.id）
        mode                    : 計時模式，傳 '番茄鐘' 或 '自訂'
        target_duration         : 目標時長（分鐘）
        start_time              : 開始時間（datetime 格式）
        end_time                : 結束時間（datetime 格式）
        total_distraction_count : 這次總共被干擾幾次
        total_distraction_time  : 這次總干擾時長（分鐘）
    回傳：
        新增的 session id
    """
    con = get_connection()
    try:
        # 計算實際讀書時長（分鐘）
        actual_duration = int((end_time - start_time).total_seconds() / 60)

        con.sql("""
            INSERT INTO sessions (
                user_id, label_id, mode, target_duration,
                start_time, end_time, actual_duration,
                total_distraction_count, total_distraction_time
            )
            VALUES (
                $user_id, $label_id, $mode, $target_duration,
                $start_time, $end_time, $actual_duration,
                $total_distraction_count, $total_distraction_time
            )
        """, params={
            'user_id'                : user_id,
            'label_id'               : label_id,
            'mode'                   : mode,
            'target_duration'        : target_duration,
            'start_time'             : start_time,
            'end_time'               : end_time,
            'actual_duration'        : actual_duration,
            'total_distraction_count': total_distraction_count,
            'total_distraction_time' : total_distraction_time
        })

        # 撈回剛剛新增的 session id
        new_id = con.sql("SELECT MAX(id) FROM sessions").fetchone()[0]

        # 更新使用者的累積時數、上次讀書時間、最近一次 session id
        con.sql("""
            UPDATE users
            SET total_hours     = total_hours + $duration,
                last_study_time = $end_time,
                last_session_id = $session_id
            WHERE id = $user_id
        """, params={
            'duration'  : actual_duration,
            'end_time'  : end_time,
            'session_id': new_id,
            'user_id'   : user_id
        })

        return new_id

    finally:
        con.close()


def save_distraction(session_id, type_id, start_time, end_time, overtime_threshold=20):
    """
    讀書被打斷時，存一筆干擾紀錄進資料庫

    參數：
        session_id         : 對應哪次讀書（save_session 回傳的 id）
        type_id            : 干擾類型編號（對應 distraction_types.id）
        start_time         : 干擾開始時間（datetime 格式）
        end_time           : 干擾結束時間（datetime 格式）
        overtime_threshold : 超時門檻（分鐘），預設 20 分鐘
    """
    con = get_connection()
    try:
        duration    = int((end_time - start_time).total_seconds() / 60)
        is_overtime = duration >= overtime_threshold

        con.sql("""
            INSERT INTO distractions (
                session_id, type_id,
                start_time, end_time, duration,
                is_overtime, is_reminded
            )
            VALUES (
                $session_id, $type_id,
                $start_time, $end_time, $duration,
                $is_overtime, FALSE
            )
        """, params={
            'session_id' : session_id,
            'type_id'    : type_id,
            'start_time' : start_time,
            'end_time'   : end_time,
            'duration'   : duration,
            'is_overtime': is_overtime
        })

    finally:
        con.close()


def check_overtime_reminder(user_id):
    """
    讀書開始前呼叫，檢查上次是否有超時干擾還沒提醒過

    回傳：
        需要提醒的干擾紀錄 DataFrame（空的話代表不需要提醒）
    """
    con = get_connection()
    try:
        result = con.sql("""
            SELECT d.id, dt.name AS type_name, d.duration
            FROM distractions d
            JOIN distraction_types dt ON d.type_id    = dt.id
            JOIN sessions          s  ON d.session_id = s.id
            WHERE s.user_id     = $user_id
              AND d.is_overtime = TRUE
              AND d.is_reminded = FALSE
        """, params={'user_id': user_id}).df()

        if len(result) > 0:
            con.sql("""
                UPDATE distractions
                SET is_reminded = TRUE
                WHERE is_overtime = TRUE
                  AND is_reminded  = FALSE
                  AND session_id IN (
                      SELECT id FROM sessions WHERE user_id = $user_id
                  )
            """, params={'user_id': user_id})

        return result

    finally:
        con.close()


# ==============================================================
# 【給遊戲化組用】
# ==============================================================

def get_exp_affection(user_id):
    """
    讀取使用者目前的經驗值和好感度

    回傳：
        {'exp': 100, 'affection': 50}
    """
    con = get_connection()
    try:
        result = con.sql("""
            SELECT exp, affection
            FROM users
            WHERE id = $user_id
        """, params={'user_id': user_id}).fetchone()

        return {'exp': result[0], 'affection': result[1]}

    finally:
        con.close()


def update_exp_affection(user_id, exp_delta, affection_delta):
    """
    更新使用者的經驗值和好感度
    傳正數代表增加，傳負數代表扣除
    好感度限制在 0~100 之間

    參數：
        exp_delta       : 經驗值變化量（例如 +10 或 -5）
        affection_delta : 好感度變化量（例如 +3 或 -2）
    """
    con = get_connection()
    try:
        # 先讀取目前的好感度
        current = con.sql("""
            SELECT affection FROM users WHERE id = $user_id
        """, params={'user_id': user_id}).fetchone()[0]

        # 用 Python 限制好感度在 0~100 之間
        new_affection = max(0, min(100, current + affection_delta))

        con.sql("""
            UPDATE users
            SET exp       = exp + $exp_delta,
                affection = $new_affection
            WHERE id = $user_id
        """, params={
            'exp_delta'    : exp_delta,
            'new_affection': new_affection,
            'user_id'      : user_id
        })

    finally:
        con.close()


def check_affection_decay(user_id, decay_threshold_hours=24, decay_amount=5):
    """
    檢查使用者是否太久沒讀書，超過門檻就自動扣好感度
    建議每次開啟 App 時呼叫

    回傳：
        True 代表有衰減，False 代表不需要衰減
    """
    con = get_connection()
    try:
        result = con.sql("""
            SELECT last_study_time
            FROM users
            WHERE id = $user_id
        """, params={'user_id': user_id}).fetchone()

        last_study_time = result[0]

        # 從來沒讀過書，不衰減
        if last_study_time is None:
            return False

        hours_passed = (datetime.now() - last_study_time).total_seconds() / 3600

        if hours_passed >= decay_threshold_hours:
            update_exp_affection(user_id, exp_delta=0, affection_delta=-decay_amount)
            return True

        return False

    finally:
        con.close()


def get_last_session_result(user_id):
    """
    讀取最近一次讀書的結果
    給遊戲化組判斷要給多少經驗值用

    回傳：
        {
            'actual_duration'        : 實際讀書時長（分鐘）,
            'target_duration'        : 目標時長（分鐘）,
            'mode'                   : 計時模式,
            'total_distraction_count': 干擾次數,
            'total_distraction_time' : 總干擾時長（分鐘）,
            'is_completed'           : 是否達成目標
        }
        沒有紀錄回傳 None
    """
    con = get_connection()
    try:
        result = con.sql("""
            SELECT actual_duration, target_duration, mode,
                   total_distraction_count, total_distraction_time
            FROM sessions
            WHERE user_id = $user_id
            ORDER BY end_time DESC
            LIMIT 1
        """, params={'user_id': user_id}).fetchone()

        if result is None:
            return None

        return {
            'actual_duration'        : result[0],
            'target_duration'        : result[1],
            'mode'                   : result[2],
            'total_distraction_count': result[3],
            'total_distraction_time' : result[4],
            'is_completed'           : result[0] >= result[1]
        }

    finally:
        con.close()


def get_story_progress(user_id):
    """
    讀取使用者目前的劇情進度

    回傳：
        {'story_id': 1, 'chapter': 3, 'branch': 'A'}
    """
    con = get_connection()
    try:
        result = con.sql("""
            SELECT story_id, chapter, branch
            FROM story_progress
            WHERE user_id = $user_id
        """, params={'user_id': user_id}).fetchone()

        return {'story_id': result[0], 'chapter': result[1], 'branch': result[2]}

    finally:
        con.close()


def update_story_progress(user_id, chapter, branch=None):
    """
    更新使用者的劇情進度

    參數：
        chapter : 解鎖到第幾章
        branch  : 目前的分歧路線（沒有分歧就傳 None）
    """
    con = get_connection()
    try:
        con.sql("""
            UPDATE story_progress
            SET chapter = $chapter,
                branch  = $branch
            WHERE user_id = $user_id
        """, params={
            'chapter': chapter,
            'branch' : branch,
            'user_id': user_id
        })

    finally:
        con.close()


# ==============================================================
# 【給介面／統計頁面用】
# ==============================================================

def get_stats(user_id):
    """
    讀取統計頁面需要的所有數據

    回傳：
        {
            'total_hours'  : 累積讀書時數（分鐘）,
            'session_count': 計時次數,
            'avg_duration' : 平均每次時長（分鐘）,
            'max_duration' : 最長一次時長（分鐘）,
            'exp'          : 累積經驗值,
            'affection'    : 好感度
        }
    """
    con = get_connection()
    try:
        user = con.sql("""
            SELECT total_hours, exp, affection
            FROM users
            WHERE id = $user_id
        """, params={'user_id': user_id}).fetchone()

        sessions = con.sql("""
            SELECT
                COUNT(id)            AS session_count,
                AVG(actual_duration) AS avg_duration,
                MAX(actual_duration) AS max_duration
            FROM sessions
            WHERE user_id = $user_id
        """, params={'user_id': user_id}).fetchone()

        return {
            'total_hours'  : user[0],
            'exp'          : user[1],
            'affection'    : user[2],
            'session_count': sessions[0] or 0,
            'avg_duration' : round(sessions[1], 1) if sessions[1] else 0,
            'max_duration' : sessions[2] or 0
        }

    finally:
        con.close()


def get_recent_sessions(user_id, limit=5):
    """
    讀取最近幾次讀書時長，用來畫長條圖

    回傳：
        DataFrame，包含 start_time 和 actual_duration 兩個欄位
    """
    con = get_connection()
    try:
        return con.sql("""
            SELECT start_time, actual_duration
            FROM sessions
            WHERE user_id = $user_id
            ORDER BY start_time DESC
            LIMIT $limit
        """, params={'user_id': user_id, 'limit': limit}).df()

    finally:
        con.close()


def get_label_summary(user_id):
    """
    統計每個標籤的總讀書時間，用來畫圓餅圖或長條圖

    回傳：
        DataFrame，包含 label_name 和 total_duration 兩個欄位
    """
    con = get_connection()
    try:
        return con.sql("""
            SELECT
                l.name                 AS label_name,
                SUM(s.actual_duration) AS total_duration
            FROM sessions s
            JOIN labels l ON s.label_id = l.id
            WHERE s.user_id = $user_id
            GROUP BY l.name
            ORDER BY total_duration DESC
        """, params={'user_id': user_id}).df()

    finally:
        con.close()


def get_distraction_summary(user_id):
    """
    統計每種干擾類型的次數和總時長，用來畫時間流失清單圖表

    回傳：
        DataFrame，包含 type_name、count、total_duration 三個欄位
    """
    con = get_connection()
    try:
        return con.sql("""
            SELECT
                dt.name         AS type_name,
                COUNT(d.id)     AS count,
                SUM(d.duration) AS total_duration
            FROM distractions d
            JOIN distraction_types dt ON d.type_id    = dt.id
            JOIN sessions          s  ON d.session_id = s.id
            WHERE s.user_id = $user_id
            GROUP BY dt.name
            ORDER BY total_duration DESC
        """, params={'user_id': user_id}).df()

    finally:
        con.close()


# ==============================================================
# 【給介面組用 — 標籤管理】
# ==============================================================

def add_label(user_id, name):
    """
    新增一個讀書標籤

    參數：
        name : 標籤名稱，例如「統計學」
    """
    con = get_connection()
    try:
        con.sql("""
            INSERT INTO labels (user_id, name)
            VALUES ($user_id, $name)
        """, params={'user_id': user_id, 'name': name})

    finally:
        con.close()


def get_labels(user_id):
    """
    讀取使用者所有的標籤清單，用來顯示下拉選單

    回傳：
        DataFrame，包含 id 和 name 兩個欄位
    """
    con = get_connection()
    try:
        return con.sql("""
            SELECT id, name
            FROM labels
            WHERE user_id = $user_id
            ORDER BY id
        """, params={'user_id': user_id}).df()

    finally:
        con.close()


def get_distraction_types():
    """
    讀取所有干擾類型選項，用來顯示下拉選單

    回傳：
        DataFrame，包含 id 和 name 兩個欄位
    """
    con = get_connection()
    try:
        return con.sql("""
            SELECT id, name
            FROM distraction_types
            ORDER BY id
        """).df()

    finally:
        con.close()