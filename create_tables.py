import duckdb

# ==============================
# 建立資料庫連線
# ==============================
con = duckdb.connect('study_app.db')

# ==============================
# 建立 Sequences（自動跳號產生器）
# 讓每次新增資料時 id 自動 +1，不用自己管
# ==============================
con.sql("CREATE SEQUENCE IF NOT EXISTS seq_users START 1;")
con.sql("CREATE SEQUENCE IF NOT EXISTS seq_labels START 1;")
con.sql("CREATE SEQUENCE IF NOT EXISTS seq_sessions START 1;")
con.sql("CREATE SEQUENCE IF NOT EXISTS seq_distractions START 1;")
con.sql("CREATE SEQUENCE IF NOT EXISTS seq_story_progress START 1;")

# ==============================
# 建立 users 資料表
# ==============================
con.sql("""
    CREATE TABLE IF NOT EXISTS users (
        id              INTEGER PRIMARY KEY DEFAULT nextval('seq_users'),
        username        TEXT UNIQUE,           -- 使用者名稱，不能重複
        exp             INTEGER   DEFAULT 0,   -- 累積經驗值
        affection       INTEGER   DEFAULT 0,   -- 好感度（0~100）
        total_hours     FLOAT     DEFAULT 0,   -- 累積讀書總時數（分鐘）
        last_session_id INTEGER   DEFAULT NULL,-- 最近一次讀書紀錄的 id
        last_study_time TIMESTAMP DEFAULT NULL -- 上次讀書時間，用來判斷好感度是否衰減
    )
""")

# ==============================
# 建立 labels 資料表
# ==============================
con.sql("""
    CREATE TABLE IF NOT EXISTS labels (
        id      INTEGER PRIMARY KEY DEFAULT nextval('seq_labels'),
        user_id INTEGER,  -- 對應 users.id
        name    TEXT      -- 標籤名稱，例如「統計學」
    )
""")

# ==============================
# 建立 distraction_types 資料表
# 選項固定，不需要自動跳號
# ==============================
con.sql("""
    CREATE TABLE IF NOT EXISTS distraction_types (
        id   INTEGER PRIMARY KEY,
        name TEXT
    )
""")

# ==============================
# 建立 sessions 資料表
# ==============================
con.sql("""
    CREATE TABLE IF NOT EXISTS sessions (
        id                      INTEGER PRIMARY KEY DEFAULT nextval('seq_sessions'),
        user_id                 INTEGER,
        label_id                INTEGER,           -- 對應 labels.id
        mode                    TEXT,              -- 計時模式：'番茄鐘' 或 '自訂'
        target_duration         INTEGER,           -- 目標時長（分鐘）
        start_time              TIMESTAMP,         -- 開始計時時間
        end_time                TIMESTAMP,         -- 結束計時時間
        actual_duration         INTEGER,           -- 實際讀書時長（分鐘）
        total_distraction_count INTEGER DEFAULT 0, -- 這次總共被干擾幾次
        total_distraction_time  INTEGER DEFAULT 0  -- 這次總干擾時長（分鐘）
    )
""")

# ==============================
# 建立 distractions 資料表
# ==============================
con.sql("""
    CREATE TABLE IF NOT EXISTS distractions (
        id          INTEGER PRIMARY KEY DEFAULT nextval('seq_distractions'),
        session_id  INTEGER,               -- 對應 sessions.id
        type_id     INTEGER,               -- 對應 distraction_types.id
        start_time  TIMESTAMP,             -- 干擾開始時間
        end_time    TIMESTAMP,             -- 干擾結束時間
        duration    INTEGER,               -- 干擾持續時長（分鐘）
        is_overtime BOOLEAN DEFAULT FALSE, -- 是否超過門檻（例如20分鐘）
        is_reminded BOOLEAN DEFAULT FALSE  -- 提醒是否已顯示過
    )
""")

# ==============================
# 建立 story_progress 資料表
# ==============================
con.sql("""
    CREATE TABLE IF NOT EXISTS story_progress (
        id       INTEGER PRIMARY KEY DEFAULT nextval('seq_story_progress'),
        user_id  INTEGER,             -- 對應 users.id
        story_id INTEGER,             -- 故事線編號（例如 1=乙女、2=恐怖）
        chapter  INTEGER DEFAULT 0,   -- 目前解鎖到第幾章
        branch   TEXT    DEFAULT NULL -- 目前所在的分歧路線
    )
""")

# ==============================
# 新增預設干擾類型選項（固定選項，不屬於任何使用者）
# ==============================
con.sql("""
    INSERT INTO distraction_types (id, name)
    VALUES
        (1, '去廁所'),
        (2, '重要訊息'),
        (3, '吃東西'),
        (4, '突發事情'),
        (5, '其他')
    ON CONFLICT (id) DO NOTHING
""")

con.close()