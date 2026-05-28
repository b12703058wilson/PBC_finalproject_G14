# pages/route_page.py — 路線選擇頁 & 輸入名字頁

import tkinter as tk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import C, ROUTE_CONFIG
from database import save_user_name, save_story_route


def build_input_page(input_frame, state, show_frame, back_fn=None):
    for w in input_frame.winfo_children():
        w.destroy()

    tk.Label(input_frame, text="請輸入你的名字",
             font=("Georgia", 20, "bold"),
             bg=C["bg"], fg=C["text"]).pack(pady=(80, 6))
    tk.Label(input_frame, text="名字會出現在劇情對話中",
             font=("Helvetica Neue", 12),
             bg=C["bg"], fg=C["text3"]).pack(pady=(0, 30))

    name_var = tk.StringVar()
    entry    = tk.Entry(input_frame, textvariable=name_var,
                        font=("Helvetica Neue", 16), relief="flat", bd=0,
                        highlightbackground=C["border2"], highlightthickness=1,
                        bg=C["surface"], fg=C["text"],
                        insertbackground=C["text"], justify="center")
    entry.pack(padx=50, ipady=10, fill="x")
    entry.focus()

    def confirm():
        name = name_var.get().strip()
        if not name:
            return
        # 取得或建立對應此名稱的真實使用者
        from data_bridge import get_or_create_user, load_user_data
        from stories import STORY_PROLOGUE, STORIES
        state.user_id   = get_or_create_user(name)
        state.user_name = name
        # 重新載入此使用者的劇情旗標（避免 guest 旗標污染）
        saved = load_user_data(state.user_id, STORY_PROLOGUE, STORIES)
        state.story_flags = saved["story_flags"]
        save_user_name(state.user_id, name)
        show_frame(input_frame)
        if back_fn:
            back_fn()

    tk.Button(input_frame, text="確認",
              font=("Helvetica Neue", 14, "bold"),
              bg=C["pink"], fg="white", activebackground=C["pink_text"],
              relief="flat", bd=0, cursor="hand2", padx=0, pady=10,
              command=confirm).pack(padx=50, pady=(16, 0), fill="x")
    entry.bind("<Return>", lambda e: confirm())
    show_frame(input_frame)


def build_route_select_page(route_frame, state, show_frame, back_fn=None):
    for w in route_frame.winfo_children():
        w.destroy()

    tk.Label(route_frame, text="選擇你的故事",
             font=("Georgia", 24, "bold"),
             bg=C["bg"], fg=C["text"]).pack(pady=(60, 6))
    tk.Label(route_frame, text="選擇後將開始解鎖對應劇情",
             font=("Helvetica Neue", 12),
             bg=C["bg"], fg=C["text3"]).pack(pady=(0, 36))

    for route_key, rc in ROUTE_CONFIG.items():
        card = tk.Frame(route_frame, bg=rc["btn_bg"],
                        highlightbackground=C["border2"], highlightthickness=1)
        card.pack(fill="x", padx=40, pady=(0, 16))
        tk.Label(card, text=rc["label"],
                 font=("Helvetica Neue", 16, "bold"),
                 bg=rc["btn_bg"], fg=rc["btn_fg"]).pack(pady=(18, 4))
        tk.Label(card, text=rc["description"],
                 font=("Helvetica Neue", 11),
                 bg=rc["btn_bg"], fg=rc["btn_fg"],
                 justify="center", wraplength=280).pack(pady=(0, 6))

        def make_choose(rk=route_key):
            def choose():
                state.story_route = rk
                save_story_route(state.user_id, rk)
                if back_fn:
                    back_fn()
            return choose

        tk.Button(card, text="選擇此故事線 →",
                  font=("Helvetica Neue", 12),
                  bg=C["surface"], fg=rc["btn_bg"],
                  activebackground=C["surface2"],
                  relief="flat", bd=0, cursor="hand2",
                  padx=14, pady=6,
                  command=make_choose()).pack(pady=(4, 18))

    show_frame(route_frame)
