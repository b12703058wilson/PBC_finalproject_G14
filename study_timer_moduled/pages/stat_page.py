# pages/stat_page.py — 統計頁（支援時間範圍切換）

import tkinter as tk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import C, get_affection_level
from game_state import fmt
from data_bridge import get_dashboard_stats

_FONTS = ['Microsoft JhengHei', 'PingFang TC', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['font.sans-serif'] = _FONTS
plt.rcParams['axes.unicode_minus'] = False
try:
    sns.set_theme(style="whitegrid", font=_FONTS[0])
except Exception:
    pass

# 時間範圍選項：顯示文字 → 天數
TIME_OPTIONS = [
    ("今天",   1),
    ("過去 7 天",   7),
    ("過去 30 天",  30),
    ("過去 90 天",  90),
]


def build_stat_page(stat_frame, state):
    for w in stat_frame.winfo_children():
        w.destroy()

    uid = getattr(state, 'user_id', None)

    # ── 目前選取的天數（用 dict 包起來讓內層函式可以修改）──
    selected = {"days": 7}

    # ── 外層容器 ───────────────────────────────────────────
    # 頂部固定區（標題 + 切換列）
    top_bar = tk.Frame(stat_frame, bg=C["bg"])
    top_bar.pack(fill="x", padx=20, pady=(16, 0))

    tk.Label(top_bar, text="📊  學習統計",
             font=("Georgia", 17, "bold"),
             bg=C["bg"], fg=C["text"]).pack(anchor="w")

    lvl = get_affection_level(state.affection)
    tk.Label(top_bar,
             text=f"{lvl['name']}　好感度 {state.affection:.0f}",
             font=("Helvetica Neue", 11),
             bg=C["bg"], fg=C["pink_text"]).pack(anchor="w", pady=(2, 10))

    # 時間範圍選單
    from tkinter import ttk

    range_bar = tk.Frame(top_bar, bg=C["bg"])
    range_bar.pack(fill="x", pady=(0, 8))

    tk.Label(range_bar, text="統計範圍：",
             font=("Helvetica Neue", 11),
             bg=C["bg"], fg=C["text2"]).pack(side="left", padx=(0, 8))

    option_labels = [label for label, _ in TIME_OPTIONS]
    option_days   = {label: days for label, days in TIME_OPTIONS}

    range_var = tk.StringVar(value=option_labels[1])   # 預設「7 天」

    range_menu = ttk.Combobox(
        range_bar,
        textvariable = range_var,
        values       = option_labels,
        state        = "readonly",
        font         = ("Helvetica Neue", 11),
        width        = 8
    )
    range_menu.pack(side="left")

    def on_range_change(event=None):
        selected["days"] = option_days[range_var.get()]
        render_charts()

    range_menu.bind("<<ComboboxSelected>>", on_range_change)

    # 分割線
    tk.Frame(top_bar, height=1, bg=C["border"]).pack(fill="x", pady=(4, 0))

    # ── 可捲動圖表區 ───────────────────────────────────────
    scroll_container = tk.Frame(stat_frame, bg=C["bg"])
    scroll_container.pack(fill="both", expand=True)

    cv = tk.Canvas(scroll_container, bg=C["bg"], highlightthickness=0)
    sb = tk.Scrollbar(scroll_container, orient="vertical", command=cv.yview)
    cv.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    cv.pack(side="left", fill="both", expand=True)

    inner = tk.Frame(cv, bg=C["bg"])
    win   = cv.create_window((0, 0), window=inner, anchor="nw")
    inner.bind("<Configure>",
               lambda e: cv.configure(scrollregion=cv.bbox("all")))
    cv.bind("<Configure>",
            lambda e: cv.itemconfig(win, width=e.width))
    cv.bind_all("<MouseWheel>",
                lambda e: cv.yview_scroll(int(-1*(e.delta/120)), "units"))

    # ── 圖表渲染函式（每次切換時間範圍都重跑）─────────────
    def render_charts():
        # 清空圖表區
        for w in inner.winfo_children():
            w.destroy()

        days = selected["days"]
        data = get_dashboard_stats(uid, days=days) if uid else {
            "core_stats": {}, "pie_chart": [], "bar_chart": [],
            "distraction_chart": [], "recent_sessions": []
        }
        cs = data["core_stats"]

        # ── 核心數字卡片 ───────────────────────────────────
        def stat_card(parent, icon, label, value):
            f = tk.Frame(parent, bg=C["surface"],
                         highlightbackground=C["border"], highlightthickness=1)
            f.pack(side="left", expand=True, fill="both", padx=4)
            tk.Label(f, text=icon, font=("Helvetica Neue", 16),
                     bg=C["surface"], fg=C["pink"]).pack(pady=(10, 2))
            tk.Label(f, text=value,
                     font=("Helvetica Neue", 13, "bold"),
                     bg=C["surface"], fg=C["text"]).pack()
            tk.Label(f, text=label, font=("Helvetica Neue", 8),
                     bg=C["surface"], fg=C["text3"]).pack(pady=(0, 10))

        total_secs = cs.get("total_hours", 0)
        avg_secs   = cs.get("avg_duration", 0)

        row1 = tk.Frame(inner, bg=C["bg"])
        row1.pack(fill="x", padx=12, pady=(14, 4))
        stat_card(row1, "⏱", "累積讀書",   fmt(total_secs))
        stat_card(row1, "📅", "總次數",     f"{cs.get('session_count', 0)} 次")
        stat_card(row1, "📈", "平均時長",   fmt(avg_secs))
        stat_card(row1, "🔥", "最長紀錄",   fmt(cs.get("max_duration", 0)))

        row2 = tk.Frame(inner, bg=C["bg"])
        row2.pack(fill="x", padx=12, pady=(0, 12))
        stat_card(row2, "✅", "零干擾次數", f"{cs.get('perfect_sessions', 0)} 次")
        stat_card(row2, "🛑", "總干擾次數", f"{cs.get('total_distraction_count', 0)} 次")
        stat_card(row2, "⭐", "總 EXP",    f"{cs.get('total_exp', 0):.0f}")
        stat_card(row2, "💕", "今日好感",  f"+{state.daily_aff_gained:.1f}")

        # ── 輔助：嵌入 matplotlib 圖表 ────────────────────
        def embed_chart(fig):
            chart_cv = FigureCanvasTkAgg(fig, master=inner)
            chart_cv.draw()
            chart_cv.get_tk_widget().pack(fill="x", padx=15, pady=(0, 16))
            plt.close(fig)

        def section_title(text):
            tk.Label(inner, text=text,
                     font=("Georgia", 13, "bold"),
                     bg=C["bg"], fg=C["text"]).pack(
                         anchor="w", padx=20, pady=(8, 2))

        # ── 1. 最近 5 次專注時長長條圖 ────────────────────
        recent = data["recent_sessions"]
        section_title("⏰  最近 5 次專注時長趨勢")
        if recent:
            df_r = pd.DataFrame(recent)
            # 自動判斷用分鐘還是小時顯示
            max_secs = df_r['actual_duration'].max()  # 此時還是秒
            if max_secs >= 3600:
                df_r['actual_duration'] = df_r['actual_duration'] / 3600
                y_label = "專注時間（小時）"
            else:
                df_r['actual_duration'] = df_r['actual_duration'] / 60
                y_label = "專注時間（分鐘）"
            df_r['display_time']    = pd.to_datetime(
                df_r['start_time']).dt.strftime('%m/%d %H:%M')

            fig1, ax1 = plt.subplots(figsize=(5.2, 3.2))
            sns.barplot(x='display_time', y='actual_duration',
                        hue='display_time', legend=False,
                        data=df_r, palette='Blues_r',
                        ax=ax1, errorbar=None)

            # ← 這個迴圈只負責標數字，不做其他事
            for p in ax1.patches:
                h = p.get_height()
                if h > 0:
                    unit = "時" if max_secs >= 3600 else "分"
                    ax1.annotate(
                        f"{h:.1f}{unit}" if max_secs >= 3600 else f"{h:.0f}{unit}",
                        (p.get_x() + p.get_width() / 2., h),
                        ha='center', va='bottom',
                        xytext=(0, 4), textcoords='offset points',
                        fontsize=8, color=C["text2"])

            # ← 這些都在迴圈外面
            ax1.set_xlabel("讀書開始時間", fontsize=9, color=C["text3"])
            ax1.set_ylabel(y_label, fontsize=9, color=C["text3"])
            ax1.tick_params(axis='x', labelsize=7, rotation=15,
                            colors=C["text3"])
            ax1.tick_params(axis='y', labelsize=8, colors=C["text3"])

            max_val = df_r['actual_duration'].max()
            ax1.set_ylim(0, max_val * 1.3 if max_val > 0 else 1)

            for sp in ax1.spines.values():
                sp.set_visible(False)
            ax1.yaxis.set_tick_params(length=0)
            ax1.xaxis.set_tick_params(length=0)
            ax1.grid(axis="y", color=C["border"], linewidth=0.7, zorder=0)

            fig1.tight_layout(pad=1.2)
            embed_chart(fig1)   # ← 只呼叫一次
        else:
            tk.Label(inner, text="尚無讀書紀錄",
                     font=("Helvetica Neue", 11),
                     bg=C["bg"], fg=C["text3"]).pack(pady=6)


        # ── 2. 各科目時間分配圓餅圖 ───────────────────────
        pie_data = data["pie_chart"]
        section_title("📚  各科目時間分配比例")
        if pie_data:
            df_p   = pd.DataFrame(pie_data)
            colors = ['#ff9999','#66b3ff','#99ff99',
                      '#ffcc99','#c2c2f0','#ffb3e6']
            fig2, ax2 = plt.subplots(figsize=(5, 3.8))
            ax2.pie(
                df_p['total_duration'],
                labels     = df_p['label_name'],
                autopct    = '%1.1f%%',
                startangle = 140,
                colors     = colors[:len(df_p)],
                textprops  = {'fontsize': 10},
                wedgeprops = {'edgecolor': 'white', 'linewidth': 1.5}
            )
            fig2.tight_layout()
            embed_chart(fig2)
        else:
            tk.Label(inner, text="尚無標籤數據，無法繪製科目圖",
                     font=("Helvetica Neue", 11),
                     bg=C["bg"], fg=C["text3"]).pack(pady=6)

        # ── 3. 干擾類型圓餅圖 ─────────────────────────────
        dist_data = data["distraction_chart"]
        section_title("🛑  干擾時間比例（時間小偷分析）")
        if dist_data:
            df_d   = pd.DataFrame(dist_data)
            colors = ['#ff6b6b','#feca57','#ff9f43','#ffff81','#ee5253']
            fig3, ax3 = plt.subplots(figsize=(5, 3.8))
            ax3.pie(
                df_d['total_duration'],
                labels     = df_d['type_name'],
                autopct    = '%1.1f%%',
                startangle = 140,
                colors     = colors[:len(df_d)],
                textprops  = {'fontsize': 10},
                wedgeprops = {'edgecolor': 'white', 'linewidth': 1.5}
            )
            fig3.tight_layout()
            embed_chart(fig3)
        else:
            tk.Label(inner, text="目前沒有干擾紀錄，表現很好！🎉",
                     font=("Helvetica Neue", 11),
                     bg=C["bg"], fg=C["text3"]).pack(pady=6)

        # ── 4. 每日讀書趨勢長條圖 ─────────────────────────
        bar_data = data["bar_chart"]
        section_title(f"📆  過去 {days} 天每日讀書趨勢")
        if bar_data:
            df_b = pd.DataFrame(bar_data)
            df_b['daily_minutes'] = df_b['daily_seconds'] / 60

            fig4, ax4 = plt.subplots(figsize=(5.2, 2.8))
            sns.barplot(x='study_date', y='daily_minutes',
                        hue='study_date', legend=False,
                        data=df_b, palette='Greens_r', ax=ax4)
            ax4.set_xlabel("日期", fontsize=9)
            ax4.set_ylabel("讀書時間（分鐘）", fontsize=9)
            ax4.tick_params(axis='x', labelsize=7,
                            rotation=20 if len(df_b) > 7 else 0)
            fig4.tight_layout()
            embed_chart(fig4)
        else:
            tk.Label(inner,
                     text=f"過去 {days} 天內沒有讀書紀錄",
                     font=("Helvetica Neue", 11),
                     bg=C["bg"], fg=C["text3"]).pack(pady=6)

        # 底部留白
        tk.Frame(inner, bg=C["bg"], height=20).pack()

        # 捲回頂部
        cv.yview_moveto(0)

    # 初始渲染
    render_charts()