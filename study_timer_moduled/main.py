# main.py — 主程式：建立視窗、導覽列、串接所有頁面
#
# 執行方式：python main.py
# 需要的套件：duckdb、matplotlib、seaborn（首次執行時自動安裝）

import subprocess
import sys

# ── 自動安裝缺少的套件 ─────────────────────────────────────
REQUIRED_PACKAGES = ["duckdb", "matplotlib", "seaborn", "pandas"]
for pkg in REQUIRED_PACKAGES:
    try:
        __import__(pkg)
    except ImportError:
        print(f"安裝 {pkg} 中，請稍等...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

import tkinter as tk

from config import C, W, H, get_affection_level
from game_state import AppState, apply_daily_decay, fmt
from data_bridge import init_db, get_or_create_user, load_user_data
from database import init_db_compat, load_db_data, save_story_flag
from stories import (STORY_PROLOGUE, STORIES, check_story_triggers,
                     get_active_stories)
from pages.timer_page  import build_timer_page
from pages.stat_page   import build_stat_page
from pages.story_page  import build_story_list_page
from pages.chat_page   import build_chat_page
from pages.route_page  import build_input_page, build_route_select_page


def main():
    # ── 初始化資料庫 ────────────────────────────────────────
    init_db()

    # ── 初始化狀態 ──────────────────────────────────────────
    state = AppState()

    # 暫用 guest 取得 user_id，等輸入名字後再更新
    # （若已有使用者名稱則在載入資料後重新對應）
    state.user_id = get_or_create_user("__guest__")

    saved = load_user_data(state.user_id, STORY_PROLOGUE, STORIES)

    # 若已有真正的使用者名稱，用真實 user_id
    if saved.get("user_name"):
        from data_bridge import get_user_by_name
        real_uid = get_user_by_name(saved["user_name"])
        if real_uid and real_uid != state.user_id:
            state.user_id = real_uid
            saved = load_user_data(state.user_id, STORY_PROLOGUE, STORIES)

    state.total_time        = saved["total_time"]
    state.session_count     = saved["session_count"]
    state.average_time      = saved["average_time"]
    state.user_name         = saved["user_name"]
    state.story_flags       = saved["story_flags"]
    state.total_exp         = saved["total_exp"]
    state.daily_exp         = saved["daily_exp"]
    state.affection         = saved["affection"]
    state.daily_aff_gained  = saved["daily_aff_gained"]
    state.last_study_date   = saved["last_study_date"]
    state.today_chat_shown  = saved["today_chat_shown"]
    state.story_route       = saved["story_route"]
    state.labels            = saved.get("labels", [])

    decay_amount = apply_daily_decay(state)

    # ── 建立視窗 ────────────────────────────────────────────
    root = tk.Tk()
    root.title("讀書計時器")
    root.geometry(f"{W}x{H}")
    root.config(bg=C["bg"])
    root.resizable(False, False)

    NAV_H        = 56
    content_area = tk.Frame(root, bg=C["bg"])
    content_area.place(x=0, y=0, width=W, height=H - NAV_H)

    # ── 頁面 Frame ──────────────────────────────────────────
    timer_frame      = tk.Frame(content_area, bg=C["bg"])
    story_frame      = tk.Frame(content_area, bg=C["bg"])
    input_frame      = tk.Frame(content_area, bg=C["bg"])
    stat_frame       = tk.Frame(content_area, bg=C["bg"])
    story_list_frame = tk.Frame(content_area, bg=C["bg"])
    chat_frame       = tk.Frame(content_area, bg=C["bg"])
    route_frame      = tk.Frame(content_area, bg=C["bg"])

    ALL_FRAMES = [timer_frame, story_frame, input_frame,
                  stat_frame, story_list_frame, chat_frame, route_frame]

    def show_frame(target):
        for f in ALL_FRAMES:
            f.pack_forget()
        target.pack(fill="both", expand=True)

    # ── 底部導覽列 ──────────────────────────────────────────
    nav = tk.Frame(root, bg=C["surface"],
                   highlightbackground=C["border"], highlightthickness=1)
    nav.place(x=0, y=H - NAV_H, width=W, height=NAV_H)
    nav_btns = {}

    def make_nav_btn(parent, label, icon, col, cmd):
        f  = tk.Frame(parent, bg=C["surface"], cursor="hand2")
        f.grid(row=0, column=col, sticky="nsew")
        parent.columnconfigure(col, weight=1)
        il = tk.Label(f, text=icon, font=("Helvetica Neue", 16),
                      bg=C["surface"], fg=C["text3"])
        il.pack(pady=(8, 0))
        tl = tk.Label(f, text=label, font=("Helvetica Neue", 9),
                      bg=C["surface"], fg=C["text3"])
        tl.pack()
        for w in [f, il, tl]:
            w.bind("<Button-1>", lambda e, c=cmd: c())
        nav_btns[label] = (il, tl)

    def set_active_nav(label):
        for lbl, (il, tl) in nav_btns.items():
            color = C["pink"] if lbl == label else C["text3"]
            il.config(fg=color)
            tl.config(fg=color)

    def open_timer():
        set_active_nav("計時")
        show_frame(timer_frame)

    def open_chat():
        set_active_nav("日常")
        build_chat_page(chat_frame, state)
        show_frame(chat_frame)

    def open_stat():
        if state.running:
            return
        set_active_nav("統計")
        build_stat_page(stat_frame, state)
        show_frame(stat_frame)

    def open_story_list():
        set_active_nav("劇情")
        build_story_list_page(story_list_frame, story_frame, state, show_frame)
        show_frame(story_list_frame)

    make_nav_btn(nav, "計時", "⏱", 0, open_timer)
    make_nav_btn(nav, "日常", "💬", 1, open_chat)
    make_nav_btn(nav, "統計", "📊", 2, open_stat)
    make_nav_btn(nav, "劇情", "📖", 3, open_story_list)

    # ── 給 timer_page 的跨頁回呼 ───────────────────────────
    all_frames_ref = {
        "build_input": lambda back_fn: (
            build_input_page(input_frame, state, show_frame, back_fn),
        ),
        "build_route": lambda back_fn: (
            build_route_select_page(route_frame, state, show_frame, back_fn),
        ),
    }

    # ── 建立計時器主頁 ──────────────────────────────────────
    trigger_story, trigger_story0, _after_prologue, _after_name = build_timer_page(
        root, timer_frame, story_frame, state, show_frame, all_frames_ref)

    set_active_nav("計時")

    # ── 好感度衰減提示 ──────────────────────────────────────
    if decay_amount > 0:
        def show_decay_toast():
            toast = tk.Label(
                content_area,
                text=f"好感度因為你的缺席下降了 {decay_amount:.0f} 點…",
                font=("Helvetica Neue", 11),
                bg="#FFF0F5", fg=C["pink_text"],
                padx=14, pady=8,
                highlightbackground=C["pink_light"],
                highlightthickness=1,
                wraplength=300)
            toast.place(relx=0.5, rely=0.1, anchor="n")
            content_area.after(3000, toast.destroy)
        root.after(500, show_decay_toast)

    # ── 啟動流程 ────────────────────────────────────────────
    prologue_done = state.story_flags.get(STORY_PROLOGUE["id"], False)

    if not prologue_done:
        trigger_story0()
    elif not state.user_name:
        build_input_page(input_frame, state, show_frame,
                         back_fn=lambda: _after_name())
    elif not state.story_route:
        build_route_select_page(route_frame, state, show_frame,
                                back_fn=lambda: show_frame(timer_frame))
    else:
        check_story_triggers(state, on_story=trigger_story)
        show_frame(timer_frame)

    root.mainloop()


if __name__ == "__main__":
    main()
