# pages/timer_page.py — 計時器主頁（含標籤選擇）

import tkinter as tk
import time
import math
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import C, ROUTE_CONFIG, get_affection_level
from game_state import fmt, fmt_min, calc_exp, calc_affection_gain, today_str, AFF_MAX
from database import save_session, save_story_flag, add_label
from stories import get_active_stories, check_story_triggers, get_story_text, pick_branch


def build_timer_page(root, timer_frame, story_frame, state,
                     show_frame, all_frames_ref):
    """
    建立計時器主頁。
    回傳 (trigger_story, trigger_story0, _after_prologue, _after_name)。
    """

    def clear():
        for w in timer_frame.winfo_children():
            w.destroy()

    clear()

    # ── 頁首 ──
    header = tk.Frame(timer_frame, bg=C["bg"])
    header.pack(fill="x", padx=20, pady=(16, 0))
    tk.Label(header, text="讀書計時器",
             font=("Georgia", 20, "bold"),
             bg=C["bg"], fg=C["text"]).pack(side="left")
    if state.story_route:
        rc = ROUTE_CONFIG[state.story_route]
        tk.Label(header, text=rc["label"].split("  ")[1],
                 font=("Helvetica Neue", 10),
                 bg=rc["btn_bg"], fg=rc["btn_fg"],
                 padx=8, pady=3).pack(side="right")

    # ── EXP + 好感度卡 ──
    status_bar = tk.Frame(timer_frame, bg=C["bg"])
    status_bar.pack(fill="x", padx=20, pady=(8, 0))

    def _make_stat_card(parent, bg, border, lbl_text, lbl_color):
        card = tk.Frame(parent, bg=bg,
                        highlightbackground=border, highlightthickness=1)
        card.pack(side="left", expand=True, fill="x", padx=(0, 6))
        top  = tk.Frame(card, bg=bg)
        top.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(top, text=lbl_text, font=("Helvetica Neue", 9),
                 bg=bg, fg=lbl_color).pack(side="left")
        val_lbl = tk.Label(top, text="0",
                           font=("Helvetica Neue", 11, "bold"),
                           bg=bg, fg=lbl_color)
        val_lbl.pack(side="right")
        bar_cv  = tk.Canvas(card, height=4, bg=C["border"], highlightthickness=0)
        bar_cv.pack(fill="x", padx=8, pady=(0, 2))
        sub_lbl = tk.Label(card, text="", font=("Helvetica Neue", 8),
                           bg=bg, fg=lbl_color)
        sub_lbl.pack(pady=(0, 4))
        return val_lbl, bar_cv, sub_lbl

    exp_val, exp_bar, exp_next = _make_stat_card(
        status_bar, C["gold_pale"], "#E8C97A", "EXP", C["gold"])
    # 好感度卡要靠右，padx 不同
    aff_card = tk.Frame(status_bar, bg=C["pink_pale"],
                        highlightbackground="#F4C0D1", highlightthickness=1)
    aff_card.pack(side="left", expand=True, fill="x", padx=(6, 0))
    aff_top = tk.Frame(aff_card, bg=C["pink_pale"])
    aff_top.pack(fill="x", padx=8, pady=(6, 2))
    tk.Label(aff_top, text="好感度", font=("Helvetica Neue", 9),
             bg=C["pink_pale"], fg=C["pink_text"]).pack(side="left")
    aff_val = tk.Label(aff_top, text=f"{state.affection:.0f}",
                       font=("Helvetica Neue", 11, "bold"),
                       bg=C["pink_pale"], fg=C["pink_text"])
    aff_val.pack(side="right")
    aff_bar = tk.Canvas(aff_card, height=4, bg=C["border"], highlightthickness=0)
    aff_bar.pack(fill="x", padx=8, pady=(0, 2))
    aff_lvl = tk.Label(aff_card, text=get_affection_level(state.affection)["name"],
                       font=("Helvetica Neue", 8),
                       bg=C["pink_pale"], fg=C["pink_text"])
    aff_lvl.pack(pady=(0, 4))

    def _draw_bar(canvas, pct, color):
        canvas.update_idletasks()
        w = canvas.winfo_width()
        if w <= 1: w = 160
        canvas.delete("bar")
        fw = max(0, int(w * pct))
        if fw > 0:
            canvas.create_rectangle(0, 0, fw, 4, fill=color, outline="", tags="bar")

    def refresh_status_bar():
        exp_val.config(text=f"{state.total_exp:.0f}")
        aff_val.config(text=f"{state.affection:.0f}")
        aff_lvl.config(text=get_affection_level(state.affection)["name"])
        nxt = next((s for s in get_active_stories(state)
                    if not state.story_flags.get(s["id"]) and s["exp_threshold"] > 0),
                   None)
        if nxt:
            pct    = min(state.total_exp / nxt["exp_threshold"], 1.0)
            remain = max(0, nxt["exp_threshold"] - state.total_exp)
            exp_next.config(text=f"下一章還差 {remain:.0f} EXP")
        else:
            pct = 1.0
            exp_next.config(text="所有章節已解鎖！")
        _draw_bar(exp_bar, pct, C["gold_bar"])
        _draw_bar(aff_bar, state.affection / AFF_MAX, C["pink_light"])

    timer_frame.after(100, refresh_status_bar)
    refresh_status_bar()

    # ── 進度環 ──
    ring_size = 190
    ring_cv = tk.Canvas(timer_frame, width=ring_size, height=ring_size,
                        bg=C["bg"], highlightthickness=0)
    ring_cv.pack(pady=(4, 0))
    elapsed_lbl = tk.Label(ring_cv, text="00:00:00",
                           font=("Georgia", 22, "bold"), bg=C["bg"], fg=C["text"])
    elapsed_lbl.place(relx=0.5, rely=0.38, anchor="center")
    tk.Label(ring_cv, text="目前連續時間",
             font=("Helvetica Neue", 10), bg=C["bg"], fg=C["text3"]
             ).place(relx=0.5, rely=0.54, anchor="center")
    total_ring_lbl = tk.Label(ring_cv, text=f"總計 {fmt(state.total_time)}",
                              font=("Helvetica Neue", 10), bg=C["bg"], fg=C["text2"])
    total_ring_lbl.place(relx=0.5, rely=0.66, anchor="center")
    cx, cy, r = ring_size // 2, ring_size // 2, 76

    def redraw_ring():
        ring_cv.delete("ring")
        nxt = next((s["exp_threshold"] for s in get_active_stories(state)
                    if s["exp_threshold"] > 0 and not state.story_flags.get(s["id"])),
                   None)
        pct = min(state.total_exp / nxt, 1.0) if nxt else 1.0
        ring_cv.create_arc(cx-r, cy-r, cx+r, cy+r, start=0, extent=359.99,
                           outline=C["border"], width=11, style="arc", tags="ring")
        if pct > 0:
            ring_cv.create_arc(cx-r, cy-r, cx+r, cy+r, start=90,
                               extent=-(pct*359.99), outline=C["gold_bar"],
                               width=11, style="arc", tags="ring")
        if pct > 0.01:
            angle = math.radians(90 - pct * 360)
            tx = cx + r * math.cos(angle)
            ty = cy - r * math.sin(angle)
            ring_cv.create_oval(tx-5, ty-5, tx+5, ty+5,
                                fill=C["gold"], outline="", tags="ring")

    # ── 標籤選擇器 ──
    from tkinter import ttk
    from config import LABEL_COLORS

    label_section = tk.Frame(timer_frame, bg=C["bg"])
    label_section.pack(fill="x", padx=20, pady=(6, 0))

    # 第一行：標題
    tk.Label(label_section, text="📌 讀書標籤",
             font=("Helvetica Neue", 11, "bold"),
             bg=C["bg"], fg=C["text2"]).pack(anchor="w", pady=(0, 4))

    # 第二行：下拉選單 + 管理按鈕
    combo_row = tk.Frame(label_section, bg=C["bg"])
    combo_row.pack(fill="x")

    label_var = tk.StringVar(value="請選擇標籤")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Label.TCombobox",
                    fieldbackground=C["surface"],
                    background=C["surface"],
                    foreground=C["text"],
                    arrowcolor=C["pink"],
                    bordercolor=C["border"],
                    padding=6)
    style.map("Label.TCombobox",
              fieldbackground=[("readonly", C["surface"])],
              foreground=[("readonly", C["text"])])

    label_combo = ttk.Combobox(
        combo_row,
        textvariable=label_var,
        style="Label.TCombobox",
        state="readonly",
        font=("Helvetica Neue", 12),
    )
    label_combo.pack(side="left", expand=True, fill="x", padx=(0, 8))

    def _update_combo():
        options = ["無標籤"] + [l["name"] for l in state.labels]
        label_combo["values"] = options
        # 如果目前選的已被刪除，重設
        if label_var.get() not in options:
            label_var.set("請選擇標籤")
            state.current_label = ""
            # 延遲呼叫，確保 _check_ready 已經定義
            timer_frame.after(0, lambda: _check_ready())

    _update_combo()

    def on_label_select(event=None):
        name = label_var.get()
        state.current_label = "" if name == "無標籤" else name
        _check_ready()

    label_combo.bind("<<ComboboxSelected>>", on_label_select)

    # 管理按鈕（點了彈出管理視窗）
    def open_label_mgr():
        mgr = tk.Toplevel(timer_frame)
        mgr.title("管理標籤")
        mgr.geometry("280x400")
        mgr.resizable(False, False)
        mgr.configure(bg=C["bg"])
        mgr.grab_set()

        def on_close():
            mgr.destroy()
            _update_combo()

        mgr.protocol("WM_DELETE_WINDOW", on_close)

        tk.Label(mgr, text="管理標籤",
                 font=("Georgia", 15, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(pady=(20, 4))
        tk.Label(mgr, text="新增或刪除讀書標籤",
                 font=("Helvetica Neue", 10),
                 bg=C["bg"], fg=C["text3"]).pack(pady=(0, 14))

        # 標籤清單
        list_frame = tk.Frame(mgr, bg=C["bg"])
        list_frame.pack(fill="both", expand=True, padx=20)

        def rebuild_list():
            for w in list_frame.winfo_children():
                w.destroy()

            if not state.labels:
                tk.Label(list_frame, text="還沒有標籤，新增一個吧！",
                         font=("Helvetica Neue", 11),
                         bg=C["bg"], fg=C["text3"]).pack(pady=20)
                return

            for i, lbl in enumerate(state.labels):
                row = tk.Frame(list_frame, bg=C["surface"],
                               highlightbackground=C["border"],
                               highlightthickness=1)
                row.pack(fill="x", pady=(0, 6))

                # 色點
                tk.Label(row, text="●",
                         font=("Helvetica Neue", 14),
                         bg=C["surface"],
                         fg=lbl.get("color", C["pink"])
                         ).pack(side="left", padx=(12, 6), pady=10)

                # 標籤名稱
                tk.Label(row, text=lbl["name"],
                         font=("Helvetica Neue", 12),
                         bg=C["surface"], fg=C["text"]
                         ).pack(side="left", expand=True, anchor="w")

                # 刪除按鈕
                def make_del(idx=i):
                    def do_del():
                        from database import save_labels
                        deleted_name = state.labels[idx]["name"]
                        if state.current_label == deleted_name:
                            state.current_label = ""
                        state.labels.pop(idx)
                        save_labels(state.user_id, state.labels)
                        rebuild_list()
                        _update_combo()
                    return do_del

                tk.Button(row, text="刪除",
                          font=("Helvetica Neue", 10),
                          bg=C["pink_pale"], fg=C["pink_text"],
                          activebackground="#F4C0D1",
                          relief="flat", bd=0, cursor="hand2",
                          padx=10, pady=6,
                          command=make_del()
                          ).pack(side="right", padx=8)

        rebuild_list()

        # 分隔線
        tk.Frame(mgr, height=1, bg=C["border"]).pack(
            fill="x", padx=20, pady=(12, 10))

        # 新增區域
        tk.Label(mgr, text="新增標籤",
                 font=("Helvetica Neue", 11, "bold"),
                 bg=C["bg"], fg=C["text2"]).pack(anchor="w", padx=20)

        add_row = tk.Frame(mgr, bg=C["bg"])
        add_row.pack(fill="x", padx=20, pady=(6, 0))

        new_name_var = tk.StringVar()
        new_entry = tk.Entry(add_row, textvariable=new_name_var,
                             font=("Helvetica Neue", 12),
                             relief="flat", bd=0,
                             highlightbackground=C["pink_light"],
                             highlightthickness=1,
                             bg=C["surface"], fg=C["text"],
                             insertbackground=C["text"],
                             width=14)
        new_entry.pack(side="left", expand=True, fill="x", ipady=7,
                       padx=(0, 8))
        new_entry.focus()

        def do_add():
            name = new_name_var.get().strip()
            if not name:
                return
            if any(l["name"] == name for l in state.labels):
                new_name_var.set("")
                return
            color = LABEL_COLORS[len(state.labels) % len(LABEL_COLORS)]
            add_label(state.user_id, name, color)
            state.labels.append({"name": name, "color": color})
            new_name_var.set("")
            rebuild_list()
            _update_combo()
            # 自動切換到剛新增的標籤
            label_var.set(name)
            state.current_label = name
            _check_ready()

        tk.Button(add_row, text="新增",
                  font=("Helvetica Neue", 12, "bold"),
                  bg=C["pink"], fg="white",
                  activebackground=C["pink_text"],
                  relief="flat", bd=0, cursor="hand2",
                  padx=14, pady=6,
                  command=do_add).pack(side="left")

        new_entry.bind("<Return>", lambda e: do_add())

        # 完成按鈕
        tk.Button(mgr, text="完成",
                  font=("Helvetica Neue", 12),
                  bg=C["surface"], fg=C["text2"],
                  activebackground=C["surface2"],
                  relief="flat", bd=0, cursor="hand2",
                  highlightbackground=C["border"],
                  highlightthickness=1,
                  padx=20, pady=8,
                  command=on_close).pack(pady=(14, 16))

    tk.Button(combo_row, text="管理",
              font=("Helvetica Neue", 11),
              bg=C["surface"], fg=C["text2"],
              activebackground=C["surface2"],
              relief="flat", bd=0, cursor="hand2",
              highlightbackground=C["border"],
              highlightthickness=1,
              padx=12, pady=6,
              command=open_label_mgr).pack(side="right")

    # ── 番茄鐘模式切換 ──
    mode_row = tk.Frame(timer_frame, bg=C["bg"])
    mode_row.pack(fill="x", padx=20, pady=(6, 0))

    # 當前模式："free" 或 "pomodoro"
    timer_mode_var = tk.StringVar(value="free")

    # 番茄鐘倒數相關狀態
    pomodoro_state = {
        "phase":      "work",   # "work" 或 "break"
        "end_time":   None,     # 這個 phase 的結束 time.time()
        "notified":   False,
    }

    def _get_pomo_label():
        w = state.pomodoro_work_minutes
        b = state.pomodoro_break_minutes
        return f"🍅  番茄鐘（{w}/{b}分）"

    pomo_btn_var = tk.StringVar(value=_get_pomo_label())

    mode_free_btn = tk.Button(
        mode_row, text="⏱  自由計時",
        font=("Helvetica Neue", 11, "bold"),
        bg=C["pink"], fg="white",
        relief="flat", bd=0, cursor="hand2", padx=10, pady=5,
        command=lambda: _switch_mode("free"))
    mode_free_btn.pack(side="left", padx=(0, 5))

    mode_pomo_btn = tk.Button(
        mode_row, textvariable=pomo_btn_var,
        font=("Helvetica Neue", 11),
        bg=C["surface"], fg=C["text"],
        relief="flat", bd=0, cursor="hand2",
        highlightbackground=C["border"], highlightthickness=1,
        padx=10, pady=5,
        command=lambda: _switch_mode("pomodoro"))
    mode_pomo_btn.pack(side="left", padx=(0, 5))

    # 番茄鐘設定按鈕
    tk.Button(
        mode_row, text="⚙",
        font=("Helvetica Neue", 13),
        bg=C["surface2"], fg=C["text3"],
        relief="flat", bd=0, cursor="hand2", padx=8, pady=4,
        command=lambda: _open_pomo_settings()
    ).pack(side="left")

    # 番茄鐘倒數標籤（只在番茄鐘模式顯示）
    pomo_countdown_var = tk.StringVar(value="")
    pomo_countdown_lbl = tk.Label(timer_frame, textvariable=pomo_countdown_var,
                                  font=("Helvetica Neue", 11, "bold"),
                                  bg=C["gold_pale"], fg=C["gold"],
                                  highlightbackground="#E8C97A", highlightthickness=1,
                                  padx=12, pady=4)

    def _switch_mode(mode):
        if state.running:
            return  # 計時中不允許切換
        timer_mode_var.set(mode)
        if mode == "free":
            mode_free_btn.config(bg=C["pink"], fg="white", font=("Helvetica Neue", 11, "bold"))
            mode_pomo_btn.config(bg=C["surface"], fg=C["text"], font=("Helvetica Neue", 11))
            pomo_countdown_lbl.pack_forget()
        else:
            mode_free_btn.config(bg=C["surface"], fg=C["text"], font=("Helvetica Neue", 11))
            mode_pomo_btn.config(bg=C["pink"], fg="white", font=("Helvetica Neue", 11, "bold"))
            pomodoro_state["phase"]    = "work"
            pomodoro_state["end_time"] = None
            pomodoro_state["notified"] = False
            pomo_countdown_lbl.pack(fill="x", padx=20, pady=(4, 0))
            _check_ready()   # ← 加在 _switch_mode 的最後一行

    def _open_pomo_settings():
        """番茄鐘時間設定彈窗。"""
        if state.running:
            return
        dlg = tk.Toplevel(timer_frame)
        dlg.title("番茄鐘設定")
        dlg.geometry("260x220")
        dlg.resizable(False, False)
        dlg.configure(bg=C["bg"])
        dlg.grab_set()

        tk.Label(dlg, text="🍅  番茄鐘設定",
                 font=("Georgia", 14, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(pady=(16, 10))

        def _row(parent, label, var):
            row = tk.Frame(parent, bg=C["bg"])
            row.pack(fill="x", padx=24, pady=4)
            tk.Label(row, text=label, font=("Helvetica Neue", 12),
                     bg=C["bg"], fg=C["text2"], width=10, anchor="w").pack(side="left")
            tk.Spinbox(row, textvariable=var, from_=1, to=90, width=5,
                       font=("Helvetica Neue", 12),
                       bg=C["surface"], fg=C["text"],
                       relief="flat", bd=0,
                       highlightbackground=C["border"], highlightthickness=1,
                       ).pack(side="left", padx=(8, 0))
            tk.Label(row, text="分鐘", font=("Helvetica Neue", 12),
                     bg=C["bg"], fg=C["text3"]).pack(side="left", padx=(4, 0))

        work_var  = tk.IntVar(value=state.pomodoro_work_minutes)
        break_var = tk.IntVar(value=state.pomodoro_break_minutes)
        _row(dlg, "工作時間", work_var)
        _row(dlg, "休息時間", break_var)

        def save_pomo():
            state.pomodoro_work_minutes  = work_var.get()
            state.pomodoro_break_minutes = break_var.get()
            pomo_btn_var.set(_get_pomo_label())
            dlg.destroy()

        tk.Button(dlg, text="儲存",
                  font=("Helvetica Neue", 12, "bold"),
                  bg=C["pink"], fg="white",
                  relief="flat", bd=0, cursor="hand2",
                  padx=20, pady=7,
                  command=save_pomo).pack(pady=(12, 0))


    # ── 開始 / 暫停按鈕 ──
    btn_row = tk.Frame(timer_frame, bg=C["bg"])
    btn_row.pack(fill="x", padx=20, pady=(8, 0))
    start_btn = tk.Button(btn_row, text="▶  開始",
              font=("Helvetica Neue", 13, "bold"),
              bg=C["border"], fg=C["text3"],
              activebackground=C["border"],
              relief="flat", bd=0, padx=0, pady=9,
              state="disabled"
              )
    start_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))
    tk.Button(btn_row, text="⏸  暫停",
              font=("Helvetica Neue", 13, "bold"),
              bg=C["surface"], fg=C["text"], activebackground=C["surface2"],
              relief="flat", bd=0, cursor="hand2",
              highlightbackground=C["border"], highlightthickness=1,
              padx=0, pady=9,
              command=lambda: _pause()
              ).pack(side="left", expand=True, fill="x", padx=(5, 0))

    # ── 提醒 ──
    notice = tk.Frame(timer_frame, bg=C["pink_pale"],
                      highlightbackground="#F4C0D1", highlightthickness=1)
    notice.pack(fill="x", padx=20, pady=(6, 0))
    tk.Label(notice, text="暫停後才會儲存紀錄，關閉前請記得暫停喔！",
             font=("Helvetica Neue", 10),
             bg=C["pink_pale"], fg=C["pink_text"],
             wraplength=340, pady=6).pack()

    def refresh_story_strip():
        pass  # mini strip 已移除

    # ── 計時邏輯 ──
    # 干擾計時上限：3 小時 = 10800 秒
    DISTRACTION_MAX_SECS = 10800

    def _check_ready():
        """確認標籤和模式都選好了，才啟用開始按鈕。"""
        label_ok = state.current_label != "" and state.current_label is not None
        # timer_mode_var 預設是 "free"，選了就算 ok
        mode_ok  = timer_mode_var.get() in ("free", "pomodoro")
        if label_ok and mode_ok:
            start_btn.config(
                bg=C["pink"], fg="white",
                activebackground=C["pink_text"],
                cursor="hand2", state="normal",
                command=lambda: _start()
            )
        else:
            start_btn.config(
                bg=C["border"], fg=C["text3"],
                activebackground=C["border"],
                cursor="arrow", state="disabled"
            )

    def _start():
        if not state.running:
            # 如果有累積的干擾時間，且低於3小時上限，顯示提醒
            if state.last_distraction_minutes > 0:
                _show_distraction_warning()
            else:
                _do_start()

    def _do_start():
        state.start_time = time.time() - state.elapsed_time
        state.running    = True
        # 清除干擾時間紀錄（已提醒過了）
        state.last_distraction_minutes = 0
        state.last_distraction_reason  = ""

    def _show_distraction_warning():
        """開始讀書前，顯示上次干擾時間過長的提醒。"""
        popup = tk.Toplevel(timer_frame)
        popup.title("干擾提醒")
        popup.geometry("300x200")
        popup.resizable(False, False)
        popup.configure(bg=C["bg"])
        popup.grab_set()

        mins = round(state.last_distraction_minutes)
        reason = state.last_distraction_reason or "干擾"

        tk.Label(popup, text="⚠️  上次干擾時間較長",
                 font=("Georgia", 14, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(pady=(20, 6))

        tk.Label(popup,
                 text=f"上次因「{reason}」暫停了約 {mins} 分鐘。\n準備好了嗎？",
                 font=("Helvetica Neue", 12),
                 bg=C["bg"], fg=C["text2"],
                 wraplength=250, justify="center").pack(pady=(0, 16))

        tk.Button(popup, text="好，開始讀書！",
                  font=("Helvetica Neue", 12, "bold"),
                  bg=C["pink"], fg="white",
                  relief="flat", bd=0, cursor="hand2",
                  padx=16, pady=8,
                  command=lambda: (popup.destroy(), _do_start())
                  ).pack()

    def _pause():
        if not state.running:
            return
        # 先暫停計時（UI 層）
        state.running = False
        # 彈出干擾原因選擇視窗
        _show_distraction_popup()

    def _cancel_pause():
        """使用者關閉彈窗（叉叉或繼續計時）：恢復計時，不記錄任何資料。"""
        state.start_time = time.time() - state.elapsed_time
        state.running    = True

    def _show_distraction_popup():
        """暫停後彈出的干擾原因選擇視窗。"""
        popup = tk.Toplevel(timer_frame)
        popup.title("暫停原因")
        popup.geometry("300x370")
        popup.resizable(False, False)
        popup.configure(bg=C["bg"])
        popup.grab_set()

        # 按右上角叉叉：視為「繼續計時」，取消此次暫停
        def on_close():
            popup.destroy()
            _cancel_pause()

        popup.protocol("WM_DELETE_WINDOW", on_close)

        tk.Label(popup, text="這次暫停的原因是？",
                 font=("Georgia", 15, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(pady=(20, 4))
        tk.Label(popup, text="選擇後會記錄此次暫停，幫助你了解干擾來源",
                 font=("Helvetica Neue", 10),
                 bg=C["bg"], fg=C["text3"]).pack(pady=(0, 12))

        # 干擾原因選項：(顯示文字, reason 字串, is_distraction)
        options = [
            ("📱  重要訊息",    "重要訊息", True),
            ("🍽  吃飯 / 休息", "吃飯",     True),
            ("💬  聊天",        "聊天",     True),
            ("📦  其他事情",    "其他",     True),
            ("✅  讀完了 / 告一段落", "告一段落", False),
        ]

        btn_frame = tk.Frame(popup, bg=C["bg"])
        btn_frame.pack(fill="x", padx=20)

        def pick(reason, is_distraction):
            popup.destroy()
            _on_distraction_chosen(reason, is_distraction)

        for label, reason, is_dist in options:
            bg     = C["surface"] if is_dist else C["teal_pale"]
            fg     = C["text"]    if is_dist else C["teal_text"]
            border = C["border"]  if is_dist else C["teal"]
            tk.Button(btn_frame, text=label,
                      font=("Helvetica Neue", 12),
                      bg=bg, fg=fg,
                      relief="flat", bd=0, cursor="hand2",
                      highlightbackground=border, highlightthickness=1,
                      anchor="w", padx=14, pady=7,
                      command=lambda r=reason, d=is_dist: pick(r, d)
                      ).pack(fill="x", pady=(0, 5))

        # 底部「繼續計時」按鈕（等同按叉叉）
        tk.Button(btn_frame, text="↩  繼續計時（不記錄）",
                  font=("Helvetica Neue", 11),
                  bg=C["bg"], fg=C["text3"],
                  relief="flat", bd=0, cursor="hand2",
                  highlightbackground=C["border"], highlightthickness=1,
                  anchor="w", padx=14, pady=6,
                  command=on_close).pack(fill="x", pady=(8, 0))

    def _on_distraction_chosen(reason, is_distraction):
        """使用者選好暫停原因後的處理。"""
        actual_secs       = state.elapsed_time
        exp_gained        = calc_exp(actual_secs, state.daily_exp)
        state.total_exp  += exp_gained
        state.daily_exp  += exp_gained
        aff_gained        = calc_affection_gain(actual_secs)
        from game_state import AFF_MAX
        state.affection   = min(AFF_MAX, state.affection + aff_gained)
        state.daily_aff_gained += aff_gained
        state.total_time    += actual_secs
        state.session_count += 1
        state.average_time   = state.total_time / state.session_count
        state.last_study_date = today_str()

        # 把本次干擾資訊暫存到 state，讓 data_bridge.save_session 可以讀到
        if is_distraction:
            if not hasattr(state, 'current_distractions') or state.current_distractions is None:
                state.current_distractions = []
            state.current_distractions.append({
                "reason": reason,
                "is_distraction": True,
            })
            if not hasattr(state, 'distraction_pause_seconds'):
                state.distraction_pause_seconds = 0
        else:
            state.current_distractions = []

        save_session(state.user_id, state, actual_secs, state.current_label)

        # 存完後清空，避免下次重複計算
        state.current_distractions      = []
        state.distraction_pause_seconds = 0
        state.elapsed_time = 0
        _after_pause(exp_gained, aff_gained)
        check_story_triggers(state, on_story=trigger_story)

        # 如果是干擾性暫停，開始後台計時
        if is_distraction:
            state.distraction_start       = time.time()
            state.last_distraction_reason = reason
        else:
            state.distraction_start = None

    def _check_distraction_timer():
        """
        每秒檢查干擾計時。
        若已超過 3 小時，停止記錄（視為緊急狀況）。
        若使用者按下開始，在 _do_start() 中讀取累積值並提醒。
        """
        if state.distraction_start is not None and not state.running:
            elapsed = time.time() - state.distraction_start
            if elapsed >= DISTRACTION_MAX_SECS:
                # 超過 3 小時：視為緊急情況，不再計算
                state.distraction_start       = None
                state.last_distraction_minutes = 0
                state.last_distraction_reason  = ""
            else:
                state.last_distraction_minutes = elapsed / 60
        elif state.running:
            # 使用者已回來讀書，停止干擾計時
            if state.distraction_start is not None:
                state.distraction_start = None
        root.after(1000, _check_distraction_timer)

    _check_distraction_timer()

    def _after_pause(exp_gained, aff_gained):
        elapsed_lbl.config(text="00:00:00")
        total_ring_lbl.config(text=f"總計 {fmt(state.total_time)}")
        refresh_status_bar()
        toast = tk.Label(timer_frame,
                         text=f"+{exp_gained:.1f} EXP　+{aff_gained:.1f} 好感度",
                         font=("Helvetica Neue", 11, "bold"),
                         bg=C["teal_pale"], fg=C["teal_text"],
                         padx=14, pady=6,
                         highlightbackground=C["teal"], highlightthickness=1)
        toast.place(relx=0.5, rely=0.97, anchor="s")
        timer_frame.after(2500, toast.destroy)

    def update_time():
        if state.running:
            state.elapsed_time = time.time() - state.start_time
            elapsed_lbl.config(text=fmt(state.elapsed_time))
            total_ring_lbl.config(text=f"總計 {fmt(state.total_time + state.elapsed_time)}")

            # 番茄鐘模式：更新倒數顯示 & 偵測時間到
            if timer_mode_var.get() == "pomodoro":
                ps = pomodoro_state
                work_secs  = state.pomodoro_work_minutes  * 60
                break_secs = state.pomodoro_break_minutes * 60

                if ps["end_time"] is None:
                    # 初始化這個 phase 的結束時間
                    phase_secs = work_secs if ps["phase"] == "work" else break_secs
                    ps["end_time"]  = time.time() + phase_secs
                    ps["notified"]  = False

                remaining = ps["end_time"] - time.time()

                if remaining <= 0 and not ps["notified"]:
                    ps["notified"] = True
                    if ps["phase"] == "work":
                        _show_pomo_notification("🍅  工作時間結束！", "休息一下吧，放鬆一下眼睛。")
                        ps["phase"]   = "break"
                    else:
                        _show_pomo_notification("⏰  休息結束！", "準備好繼續讀書了嗎？")
                        ps["phase"]   = "work"
                    ps["end_time"] = None

                if remaining > 0:
                    phase_label = "工作中" if ps["phase"] == "work" else "休息中"
                    pomo_countdown_var.set(
                        f"{phase_label}  剩餘 {fmt(max(0, remaining))}"
                    )

        redraw_ring()
        root.after(1000, update_time)

    def _show_pomo_notification(title, message):
        """番茄鐘時間到的通知彈窗。"""
        popup = tk.Toplevel(timer_frame)
        popup.title("番茄鐘")
        popup.geometry("280x160")
        popup.resizable(False, False)
        popup.configure(bg=C["gold_pale"])
        popup.attributes("-topmost", True)

        tk.Label(popup, text=title,
                 font=("Georgia", 14, "bold"),
                 bg=C["gold_pale"], fg=C["gold"]).pack(pady=(20, 6))
        tk.Label(popup, text=message,
                 font=("Helvetica Neue", 12),
                 bg=C["gold_pale"], fg=C["text2"]).pack()
        tk.Button(popup, text="好的",
                  font=("Helvetica Neue", 12, "bold"),
                  bg=C["gold"], fg="white",
                  relief="flat", bd=0, cursor="hand2",
                  padx=20, pady=7,
                  command=popup.destroy).pack(pady=(16, 0))
        # 10 秒後自動關閉
        popup.after(10000, lambda: popup.destroy() if popup.winfo_exists() else None)

    update_time()

    # ── 劇情觸發 queue ──
    story_queue = []

    def play_next_story():
        if not story_queue:
            refresh_story_strip()
            refresh_status_bar()
            show_frame(timer_frame)
            return
        story_def   = story_queue.pop(0)
        parent_id   = story_def.get("parent_id", story_def["id"])
        branch_id   = story_def.get("branch_id")

        def on_finished():
            state.story_flags[parent_id] = True
            save_story_flag(state.user_id, parent_id, True)
            if branch_id:
                state.story_flags[branch_id] = True
                save_story_flag(state.user_id, branch_id, True)
            play_next_story()

        _show_story(story_def, on_finished)

    def trigger_story(story_def):
        story_queue.append(story_def)
        if len(story_queue) == 1:
            play_next_story()

    def _show_story(story_def, on_finished):
        from config import ROUTE_CONFIG
        cfg      = ROUTE_CONFIG.get(state.story_route, ROUTE_CONFIG["romance"])
        story_bg = cfg["story_bg"]
        story_fg = cfg["story_fg"]
        route    = state.story_route

        timer_frame.pack_forget()
        for w in story_frame.winfo_children():
            w.destroy()
        story_frame.configure(bg=story_bg)
        story_frame.pack(fill="both", expand=True)

        text_list = get_story_text(story_def, state.user_name)
        current   = {"index": 0}

        tk.Label(story_frame,
                 text=f"{story_def['title']}　{story_def['subtitle']}",
                 font=("Georgia", 13, "italic"),
                 bg=story_bg,
                 fg=C["pink_text"] if route == "romance" else "#9B7FA6"
                 ).place(x=20, y=18)
        tk.Frame(story_frame, height=1, bg=C["border"]).place(x=20, y=44, width=360)

        text_lbl = tk.Label(story_frame, text=text_list[0],
                            wraplength=330, font=("Georgia", 15),
                            justify="left", bg=story_bg, fg=story_fg,
                            padx=30, pady=20)
        text_lbl.place(x=0, y=60, width=400, height=480)

        prog_lbl = tk.Label(story_frame, text=f"1 / {len(text_list)}",
                            font=("Helvetica Neue", 11), bg=story_bg, fg=C["gray"])
        prog_lbl.place(x=0, y=560, width=400)

        hint = tk.Label(story_frame, text="點擊畫面繼續 →",
                        font=("Helvetica Neue", 11), bg=story_bg,
                        fg=C["pink_light"] if route == "romance" else "#9B7FA6")
        hint.place(x=0, y=585, width=400)

        def next_text(event=None):
            current["index"] += 1
            if current["index"] < len(text_list):
                text_lbl.config(text=text_list[current["index"]])
                prog_lbl.config(text=f"{current['index']+1} / {len(text_list)}")
            else:
                on_finished()
                story_frame.pack_forget()

        for w in [story_frame, text_lbl, prog_lbl, hint]:
            w.bind("<Button-1>", next_text)

    def trigger_story0():
        from stories import STORY_PROLOGUE
        s0 = STORY_PROLOGUE
        def on_finished():
            state.story_flags[s0["id"]] = True
            save_story_flag(state.user_id, s0["id"], True)
            _after_prologue()
        _show_story(s0, on_finished)

    def _after_prologue():
        if not state.user_name:
            # 由 main 提供 build_input_page，透過 all_frames_ref 呼叫
            all_frames_ref["build_input"](back_fn=lambda: _after_name())
        else:
            _after_name()

    def _after_name():
        if not state.story_route:
            all_frames_ref["build_route"](back_fn=lambda: show_frame(timer_frame))
        else:
            show_frame(timer_frame)

    return trigger_story, trigger_story0, _after_prologue, _after_name
