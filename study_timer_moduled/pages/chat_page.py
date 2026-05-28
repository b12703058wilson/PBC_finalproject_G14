# pages/chat_page.py — 日常劇情聊天頁

import tkinter as tk
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import C, get_affection_level
from game_state import today_str
from stories import DAILY_CHATS_ROMANCE, DAILY_CHATS_HORROR


def build_chat_page(chat_frame, state):
    for w in chat_frame.winfo_children():
        w.destroy()

    is_horror = (state.story_route == "horror")

    # ── 路線對應的樣式設定 ──
    if is_horror:
        bg_main    = C["horror_bg"]       # 深藍黑
        bg_chat    = "#12121F"
        bg_bubble  = "#1E1E35"
        bg_header  = "#0E0E1C"
        fg_text    = C["horror_text"]     # 米白
        fg_sub     = "#7A7A9A"
        fg_avatar  = "#8B6FC6"
        avatar_bg  = "#2D1B4E"
        border_col = "#2D2D4E"
        divider_col = "#2D2D4E"
        char_name  = "？？？"
        aff_color  = "#8B6FC6"
        aff_prefix = "👁"
    else:
        bg_main    = C["surface2"]
        bg_chat    = C["surface2"]
        bg_bubble  = C["bubble_char"]
        bg_header  = C["surface"]
        fg_text    = C["text"]
        fg_sub     = C["pink_text"]
        fg_avatar  = "white"
        avatar_bg  = C["pink_light"]
        border_col = C["border"]
        divider_col = C["border"]
        char_name  = "林霽安"
        aff_color  = C["pink_text"]
        aff_prefix = "♥"

    chat_frame.configure(bg=bg_main)

    # ── 頁首 ──
    header = tk.Frame(chat_frame, bg=bg_header,
                      highlightbackground=border_col, highlightthickness=1)
    header.pack(fill="x")

    name_lbl = tk.Label(header, text=char_name,
                        font=("Georgia", 15, "bold"),
                        bg=bg_header, fg=fg_text)
    name_lbl.pack(side="left", padx=16, pady=12)

    lvl = get_affection_level(state.affection)
    tk.Label(header,
             text=f"{aff_prefix} {lvl['name']}　好感度 {state.affection:.0f}",
             font=("Helvetica Neue", 10),
             bg=bg_header, fg=aff_color).pack(side="right", padx=16)

    # ── 聊天區域 ──
    chat_outer = tk.Frame(chat_frame, bg=bg_chat)
    chat_outer.pack(fill="both", expand=True)
    chat_cv = tk.Canvas(chat_outer, bg=bg_chat, highlightthickness=0)
    chat_sb = tk.Scrollbar(chat_outer, orient="vertical", command=chat_cv.yview)
    chat_cv.configure(yscrollcommand=chat_sb.set)
    chat_sb.pack(side="right", fill="y")
    chat_cv.pack(side="left", fill="both", expand=True)

    msg_area = tk.Frame(chat_cv, bg=bg_chat)
    msg_win  = chat_cv.create_window((0, 0), window=msg_area, anchor="nw")
    msg_area.bind("<Configure>", lambda e: (
        chat_cv.configure(scrollregion=chat_cv.bbox("all")),
        chat_cv.itemconfig(msg_win, width=chat_cv.winfo_width())))
    chat_cv.bind("<Configure>",
                 lambda e: chat_cv.itemconfig(msg_win, width=e.width))

    # 恐怖向頭像文字（短橫線比字母更神秘）
    avatar_char = "？" if is_horror else "霽"

    def add_bubble(text):
        row = tk.Frame(msg_area, bg=bg_chat)
        row.pack(fill="x", padx=12, pady=(6, 0), anchor="w")
        tk.Label(row, text=avatar_char,
                 font=("Georgia", 11, "bold"),
                 bg=avatar_bg, fg=fg_avatar,
                 width=2, height=1, padx=4, pady=4).pack(side="left", anchor="n")
        tk.Label(row, text=text,
                 font=("Helvetica Neue", 12),
                 bg=bg_bubble, fg=fg_text,
                 wraplength=240, justify="left",
                 padx=12, pady=8,
                 highlightbackground=border_col,
                 highlightthickness=1).pack(side="left", padx=(6, 0))

    def add_divider(text):
        row = tk.Frame(msg_area, bg=bg_chat)
        row.pack(fill="x", padx=20, pady=(12, 4))
        tk.Frame(row, bg=divider_col, height=1).pack(side="left", expand=True, fill="x")
        tk.Label(row, text=f"  {text}  ",
                 font=("Helvetica Neue", 9),
                 bg=bg_chat, fg=fg_sub).pack(side="left")
        tk.Frame(row, bg=divider_col, height=1).pack(side="left", expand=True, fill="x")

    def scroll_bottom():
        chat_cv.update_idletasks()
        chat_cv.yview_moveto(1.0)

    add_divider("今天")

    # 根據路線選對應的日常對話資料
    daily_pool = DAILY_CHATS_HORROR if is_horror else DAILY_CHATS_ROMANCE
    lvl_name   = get_affection_level(state.affection)["name"]
    pool       = daily_pool.get(lvl_name, daily_pool["陌生"])
    random.seed(int(today_str().replace("-", "")))
    chosen     = random.choice(pool)

    def show_messages(messages, idx=0):
        if idx >= len(messages):
            if not state.today_chat_shown:
                state.today_chat_shown = True
                from database import save_today_chat_shown
                save_today_chat_shown(state.user_id)
            scroll_bottom()
            return
        add_bubble(messages[idx])
        scroll_bottom()
        # 恐怖向訊息間隔稍長，增加氣氛
        delay = 1100 if is_horror else 800
        chat_frame.after(delay, lambda: show_messages(messages, idx + 1))

    show_messages(chosen)

    # ── 底部輸入欄 ──
    input_bar = tk.Frame(chat_frame, bg=bg_header,
                         highlightbackground=border_col, highlightthickness=1)
    input_bar.pack(fill="x", side="bottom")
    placeholder = "選項回覆功能開發中…" if not is_horror else "……"
    tk.Label(input_bar, text=placeholder,
             font=("Helvetica Neue", 11),
             bg=bg_header, fg=fg_sub, pady=12).pack()
