# pages/story_page.py — 劇情進度頁

import tkinter as tk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import C, ROUTE_CONFIG, get_affection_level
from stories import get_active_stories, get_story_text, pick_branch


def build_story_list_page(story_list_frame, story_frame, state, show_frame):
    for w in story_list_frame.winfo_children():
        w.destroy()

    tk.Label(story_list_frame, text="劇情進度",
             font=("Georgia", 18, "bold"),
             bg=C["bg"], fg=C["text"]).pack(anchor="w", padx=20, pady=(16, 0))
    tk.Frame(story_list_frame, height=1, bg=C["border"]).pack(
        fill="x", padx=20, pady=(10, 0))

    stories = get_active_stories(state)
    if not stories:
        tk.Label(story_list_frame, text="尚未選擇故事線",
                 font=("Helvetica Neue", 13),
                 bg=C["bg"], fg=C["text3"]).pack(pady=60)
        return

    done_count  = sum(1 for s in stories if state.story_flags.get(s["id"]))
    total_count = len(stories)
    route_label = ROUTE_CONFIG.get(state.story_route, {}).get("label", "")

    tk.Label(story_list_frame,
             text=f"{route_label}  ·  已解鎖 {done_count} / {total_count} 章",
             font=("Helvetica Neue", 12),
             bg=C["bg"], fg=C["text2"]).pack(anchor="w", padx=24, pady=(8, 2))

    prog_bg = tk.Frame(story_list_frame, bg=C["border"], height=4)
    prog_bg.pack(fill="x", padx=20, pady=(0, 12))
    tk.Frame(prog_bg, bg=C["pink"], height=4).place(
        relwidth=done_count / total_count if total_count else 0, relheight=1)

    # 可捲動區域
    outer = tk.Frame(story_list_frame, bg=C["bg"])
    outer.pack(fill="both", expand=True, padx=20)
    cs = tk.Canvas(outer, bg=C["bg"], highlightthickness=0)
    sb = tk.Scrollbar(outer, orient="vertical", command=cs.yview)
    cs.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    cs.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(cs, bg=C["bg"])
    cs.create_window((0, 0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda e: cs.configure(scrollregion=cs.bbox("all")))
    cs.bind_all("<MouseWheel>",
                lambda e: cs.yview_scroll(int(-1*(e.delta/120)), "units"))

    for s in stories:
        sid  = s["id"]
        done = state.story_flags.get(sid, False)

        card = tk.Frame(inner, bg=C["surface"],
                        highlightbackground=C["border"], highlightthickness=1)
        card.pack(fill="x", pady=(0, 10))
        tk.Frame(card, bg=C["teal"] if done else C["border2"],
                 width=4).pack(side="left", fill="y")

        body = tk.Frame(card, bg=C["surface"])
        body.pack(side="left", fill="both", expand=True, padx=14, pady=12)

        title_row = tk.Frame(body, bg=C["surface"])
        title_row.pack(fill="x")
        tk.Label(title_row, text=s["title"],
                 font=("Helvetica Neue", 10), bg=C["surface"],
                 fg=C["teal_text"] if done else C["text3"]).pack(side="left")
        status_text = ("✓ 已解鎖" if done else
                       ("🔒 未解鎖" if s["exp_threshold"] > 0 else "🔓 可解鎖"))
        tk.Label(title_row, text=status_text,
                 font=("Helvetica Neue", 10), bg=C["surface"],
                 fg=C["teal"] if done else C["gray"]).pack(side="right")

        tk.Label(body, text=s["subtitle"],
                 font=("Georgia", 14, "bold"), bg=C["surface"],
                 fg=C["text"] if done else C["text3"]
                 ).pack(anchor="w", pady=(2, 0))

        if not done and s["exp_threshold"] > 0:
            need   = s["exp_threshold"]
            cur    = min(state.total_exp, need)
            pct    = cur / need
            remain = max(0, need - state.total_exp)
            tk.Label(body,
                     text=f"還差 {remain:.0f} EXP 解鎖（累積 {cur:.0f} / {need:.0f}）",
                     font=("Helvetica Neue", 10),
                     bg=C["surface"], fg=C["gold"]).pack(anchor="w", pady=(4, 2))
            bar_bg = tk.Frame(body, bg=C["gold_pale"], height=4)
            bar_bg.pack(fill="x", pady=(0, 2))
            tk.Frame(bar_bg, bg=C["gold_bar"], height=4).place(
                relwidth=pct, relheight=1)

        req = s.get("requires")
        if not done and req and not state.story_flags.get(req):
            req_s = next((x for x in stories if x["id"] == req), None)
            if req_s:
                tk.Label(body, text=f"需先解鎖「{req_s['title']}」",
                         font=("Helvetica Neue", 9),
                         bg=C["surface"], fg=C["text3"]).pack(anchor="w")

        if done:
            def make_replay(story_def=s):
                def replay():
                    if "branches" in story_def:
                        seen = next(
                            (b for b in story_def["branches"]
                             if state.story_flags.get(b["id"])),
                            None)
                        target = ({**story_def, **seen} if seen
                                  else {**story_def,
                                        **pick_branch(story_def["branches"], state)})
                    else:
                        target = story_def
                    _show_story_replay(target, story_def, story_frame,
                                       story_list_frame, state, show_frame)
                return replay

            tk.Button(body, text="複習劇情",
                      font=("Helvetica Neue", 11),
                      bg=C["pink_pale"], fg=C["pink_text"],
                      activebackground="#F4C0D1", relief="flat", bd=0,
                      cursor="hand2", highlightbackground="#F4C0D1",
                      highlightthickness=1, padx=12, pady=5,
                      command=make_replay()).pack(anchor="w", pady=(8, 0))


def _show_story_replay(story_def, parent_def, story_frame,
                       prev_frame, state, show_frame):
    cfg      = ROUTE_CONFIG.get(state.story_route, ROUTE_CONFIG["romance"])
    story_bg = cfg["story_bg"]
    story_fg = cfg["story_fg"]
    route    = state.story_route

    prev_frame.pack_forget()
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
            story_frame.pack_forget()
            show_frame(prev_frame)

    for w in [story_frame, text_lbl, prog_lbl, hint]:
        w.bind("<Button-1>", next_text)
