# config.py — 設計系統、路線設定、好感度階層

W, H = 400, 680

# ── 顏色系統 ──────────────────────────────────────────────────
C = {
    "bg":          "#FAFAF8",
    "surface":     "#FFFFFF",
    "surface2":    "#F5F3EE",
    "border":      "#E8E4DE",
    "border2":     "#D5CFC6",
    "pink":        "#D4537E",
    "pink_light":  "#ED93B1",
    "pink_pale":   "#FBEAF0",
    "pink_text":   "#993556",
    "teal":        "#1D9E75",
    "teal_pale":   "#E1F5EE",
    "teal_text":   "#0F6E56",
    "gold":        "#C8922A",
    "gold_pale":   "#FDF3E0",
    "gold_bar":    "#E8B84B",
    "gray":        "#888780",
    "gray_pale":   "#F1EFE8",
    "gray_text":   "#5F5E5A",
    "text":        "#2C2C2A",
    "text2":       "#5F5E5A",
    "text3":       "#888780",
    "bubble_char": "#FFF0F5",
    "horror_bg":   "#1A1A2E",
    "horror_text": "#E8D5B7",
    "horror_btn":  "#2D1B4E",
}

# 標籤顏色池（循環使用）
LABEL_COLORS = [
    "#D4537E", "#5B8CDB", "#2EAA76", "#E07B39",
    "#8B5CF6", "#E4B84B", "#3BBFBF", "#C45C8A",
]

# ── 路線設定 ──────────────────────────────────────────────────
ROUTE_CONFIG = {
    "romance": {
        "label":       "🌸  乙女向",
        "description": "與角色漸漸拉近距離。\n透過每次的讀書，解鎖更多故事。",
        "btn_bg":      "#D4537E",
        "btn_fg":      "#FFFFFF",
        "story_bg":    "#FFF9F3",
        "story_fg":    "#4A1B0C",
    },
    "horror": {
        "label":       "🕯  恐怖向",
        "description": "有些東西不該被發現。\n繼續讀下去，如果你敢的話。",
        "btn_bg":      "#2C2C3E",
        "btn_fg":      "#E8D5B7",
        "story_bg":    "#1A1A2E",
        "story_fg":    "#E8D5B7",
    },
}

# ── 好感度階層 ────────────────────────────────────────────────
AFFECTION_LEVELS = [
    {"threshold": 0,  "name": "陌生", "desc": "對方對你還不太熟悉……"},
    {"threshold": 20, "name": "禮貌", "desc": "對方以禮相待，但仍保持距離。"},
    {"threshold": 40, "name": "親近", "desc": "對方開始對你展露笑容。"},
    {"threshold": 60, "name": "信任", "desc": "對方願意和你分享心事了。"},
    {"threshold": 80, "name": "親密", "desc": "對方在你身邊感到很自在。"},
]

def get_affection_level(aff: float) -> dict:
    current = AFFECTION_LEVELS[0]
    for lvl in AFFECTION_LEVELS:
        if aff >= lvl["threshold"]:
            current = lvl
    return current
