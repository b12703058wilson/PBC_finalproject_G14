import matplotlib.pyplot as plt
import seaborn as sns

# 核心關鍵：匯入你們 db_manager.py 裡的統計 DataFrame 函式
from data_bridge import get_recent_sessions, get_label_summary, get_distraction_summary

# ==============================================================
# 圖表美化與中文防亂碼設定
# ==============================================================
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Arial Unicode MS'] # 支援 Windows/Mac 中文
plt.rcParams['axes.unicode_minus'] = False 
sns.set_theme(style="whitegrid", font="Microsoft JhengHei") 

# ==============================================================
# 1. 【最後總結讀書時間】最近 5 次專注時長趨勢圖 (長條圖)
# ==============================================================
def generate_recent_sessions_chart(user_id):
    df = get_recent_sessions(user_id, limit=5)
    if df.empty:
        print("尚無讀書紀錄，無法繪製時長長條圖。")
        return None
        
    df = df.iloc[::-1].reset_index(drop=True) # 時間由舊到新排序
    df['display_time'] = df['start_time'].dt.strftime('%m/%d %H:%M')
    
    plt.figure(figsize=(7, 4))
    ax = sns.barplot(x='display_time', y='actual_duration', data=df, palette='Blues_r')
    
    for p in ax.patches:
        ax.annotate(f"{int(p.get_height())} 分", 
                    (p.get_x() + p.get_width() / 2., p.get_height()), 
                    ha='center', va='center', xytext=(0, 5), textcoords='offset points', fontsize=10)
                    
    plt.title("⏰ 最近 5 次專注時長趨勢圖", fontsize=13, fontweight='bold', pad=15)
    plt.xlabel("讀書開始時間", fontsize=10)
    plt.ylabel("實際專注時間 (分鐘)", fontsize=10)
    plt.tight_layout()
    
    filename = 'chart_recent_sessions.png'
    plt.savefig(filename, dpi=300)
    plt.close()
    return filename

# ==============================================================
# 2. 【多維度標籤視覺化】各科目時間分配比例 (圓餅圖)
# ==============================================================
def generate_label_pie_chart(user_id):
    df = get_label_summary(user_id)
    if df.empty:
        print("尚無標籤數據，無法繪製學科圓餅圖。")
        return None
        
    plt.figure(figsize=(5, 5))
    colors = ['#ff9999','#66b3ff','#99ff99','#ffcc99','#c2c2f0','#ffb3e6']
    
    plt.pie(
        df['total_duration'], 
        labels=df['label_name'], 
        autopct='%1.1f%%', 
        startangle=140, 
        colors=colors[:len(df)],
        textprops={'fontsize': 11},
        wedgeprops={'edgecolor': 'white', 'linewidth': 1.5}
    )
    
    plt.title("📚 各科目時間分配比例", fontsize=13, fontweight='bold', pad=15)
    plt.tight_layout()
    
    filename = 'chart_label_pie.png'
    plt.savefig(filename, dpi=300)
    plt.close()
    return filename

# ==============================================================
# 3. 【pie chart 紀錄干擾時間比例】(圓餅圖)
# ==============================================================
def generate_distraction_pie_chart(user_id):
    df = get_distraction_summary(user_id)
    if df.empty:
        print("目前沒有任何分心紀錄，無法繪製干擾圖。")
        return None
        
    plt.figure(figsize=(5, 5))
    # 暖色系配色，符合「干擾/警告」的意象
    colors = ['#ff6b6b', '#feca57', '#ff9f43', '#ffff81', '#ee5253']
    
    plt.pie(
        df['total_duration'], 
        labels=df['type_name'], 
        autopct='%1.1f%%', 
        startangle=140, 
        colors=colors[:len(df)],
        textprops={'fontsize': 11},
        wedgeprops={'edgecolor': 'white', 'linewidth': 1.5}
    )
    
    plt.title("🛑 紀錄干擾時間比例 (時間小偷分析)", fontsize=13, fontweight='bold', pad=15)
    plt.tight_layout()
    
    filename = 'chart_distraction_pie.png'
    plt.savefig(filename, dpi=300)
    plt.close()
    return filename
