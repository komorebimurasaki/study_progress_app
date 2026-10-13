import streamlit as st
import pandas as pd
from datetime import datetime, date
import requests
import json

st.set_page_config(page_title="定期テスト 計画＆進捗管理アプリ", layout="wide")

# --- 🔌 GAS（ウェブアプリ）のURL設定 ---
GAS_URL = "https://script.google.com/macros/s/AKfycby18d2CsK58l_toJ7OYiK1Lp359j804g0O4uMmftybv6FgPTg8g08hG-AYXuUG3AeZQ/exec"

# --- 🖨️ 印刷時のスタイル・A4収まり＆切れ防止設定 ---
st.markdown("""
<style>
@media print {
    [data-testid="stSidebar"] {
        display: none !important;
    }
    header, footer, .stActionButton {
        display: none !important;
    }
    .no-print {
        display: none !important;
    }
    /* A4 1枚に収めるための全体縮小とマージン調整 */
    body {
        zoom: 75%;
    }
    .print-container {
        page-break-inside: avoid;
    }
}
</style>
""", unsafe_allow_html=True)

st.title("📚 定期テスト 計画＆進捗管理アプリ")

# 初期データの設定（教科ごとのデフォルト値）
subjects_config = [
    {"教科": "国語", "中間末尾": 20, "期末末尾": 39, "目標周回": 3, "授業進度": 15},
    {"教科": "数学", "中間末尾": 18, "期末末尾": 37, "目標周回": 3, "授業進度": 16},
    {"教科": "英語", "中間末尾": 15, "期末末尾": 31, "目標周回": 3, "授業進度": 12},
    {"教科": "理科", "中間末尾": 17, "期末末尾": 34, "目標周回": 3, "授業進度": 14},
    {"教科": "地理", "中間末尾": 12, "期末末尾": 25, "目標周回": 3, "授業進度": 10},
    {"教科": "歴史", "中間末尾": 6, "期末末尾": 13, "目標周回": 3, "授業進度": 5},
]

# --- スプレッドシートから設定データを取得 ---
@st.cache_data(ttl=3)
def load_settings_from_gas():
    try:
        response = requests.post(GAS_URL, json={"action": "read_settings"})
        return response.json()
    except:
        return {}

db_settings = load_settings_from_gas()

def save_setting_to_gas(key, value):
    try:
        payload = {"action": "save_setting", "key": key, "value": str(value)}
        requests.post(GAS_URL, json=payload)
        st.cache_data.clear()
    except Exception as e:
        print(f"Setting save error: {e}")

# --- 1. サイドバー：画面モード切替 ＆ テスト段階・期限の設定 ---
st.sidebar.header("🖥️ 表示モード切替")
app_mode = st.sidebar.radio("表示する画面を選択", options=["📝 チェックリスト画面", "🖨️ サマリー・進捗一覧印刷画面"], key="selected_app_mode")

st.sidebar.divider()

st.sidebar.header("🗓️ テスト段階・期限の設定")
test_stage = st.sidebar.radio("管理するテストを選択", options=["中間テスト", "期末テスト"], key="selected_test_stage")

date_key = f"target_date_{test_stage}"
saved_date_str = db_settings.get(date_key)
if saved_date_str:
    try:
        default_date = datetime.strptime(saved_date_str[:10], "%Y-%m-%d").date()
    except:
        default_date = date.today()
else:
    default_date = date.today()

target_date = st.sidebar.date_input(f"{test_stage} 予定日", value=default_date, key=date_key)

if str(target_date) != str(saved_date_str):
    save_setting_to_gas(date_key, target_date)

today = date.today()
remaining_days = (target_date - today).days
if remaining_days <= 0:
    remaining_days = 1
    st.sidebar.warning("⚠️ 予定日が本日以前になっています。")
else:
    st.sidebar.info(f"⏳ {test_stage} まで **あと {remaining_days} 日** です！")

st.sidebar.divider()
st.sidebar.subheader(f"✏️ {test_stage} の範囲 ＆ 進度設定")

subject_settings = {}
for item in subjects_config:
    subj = item["教科"]
    st.sidebar.markdown(f"--- **{subj}** ---")
    
    start_p = 2
    default_end = item["期末末尾"] if test_stage == "期末テスト" else item["中間末尾"]
    
    end_key = f"end_p_{test_stage}_{subj}"
    school_key = f"school_p_{test_stage}_{subj}"
    round_key = f"round_{test_stage}_{subj}"
    
    saved_end = int(db_settings.get(end_key, default_end))
    saved_school = int(db_settings.get(school_key, min(item["授業進度"], saved_end)))
    saved_round = int(db_settings.get(round_key, item["目標周回"]))
    
    end_p = st.sidebar.number_input(f"{subj} 末尾P", min_value=1, max_value=300, value=saved_end, key=end_key)
    if end_p != saved_end:
        save_setting_to_gas(end_key, end_p)
        
    current_school_p = st.sidebar.number_input(f"{subj} の授業進度 (~p)", min_value=start_p, max_value=end_p, value=min(saved_school, end_p), key=school_key)
    if current_school_p != saved_school:
        save_setting_to_gas(school_key, current_school_p)
        
    target_round = st.sidebar.selectbox(f"{subj} の目標周回", options=[1, 2, 3], index=saved_round-1, key=round_key)
    if target_round != saved_round:
        save_setting_to_gas(round_key, target_round)
    
    subject_settings[subj] = {
        "start": start_p,
        "end": end_p,
        "school_progress": current_school_p,
        "target_round": target_round
    }

# --- 2. スプレッドシートからのチェックデータ読み込み ---
@st.cache_data(ttl=3)
def load_data_from_gas():
    try:
        response = requests.post(GAS_URL, json={"action": "read"})
        data = response.json()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame(columns=["test_stage", "subject", "round", "page", "checked"])

df_db = load_data_from_gas()

# --- 3. 共通計算データ作成 ---
updated_rows = []

for i, item in enumerate(subjects_config):
    subj = item["教科"]
    s_p = subject_settings[subj]["start"]
    e_p = subject_settings[subj]["end"]
    school_p = subject_settings[subj]["school_progress"]
    t_round = subject_settings[subj]["target_round"]
    
    page_blocks = []
    current = s_p
    while current <= e_p:
        next_p = min(current + 1, e_p)
        page_blocks.append((current, next_p))
        current += 2
        
    pages_per_round = len(page_blocks)
    total_items_count = pages_per_round * t_round
    
    checked_count = 0
    for r in range(1, t_round + 1):
        for p_start, p_end in page_blocks:
            is_currently_checked = False
            if not df_db.empty and all(col in df_db.columns for col in ["test_stage", "subject", "round", "page", "checked"]):
                matched = df_db[(df_db["test_stage"].astype(str) == str(test_stage)) & 
                                (df_db["subject"].astype(str) == str(subj)) & 
                                (df_db["round"].astype(str) == str(r)) & 
                                (df_db["page"].astype(str) == str(p_end))]
                if not matched.empty:
                    val = matched.iloc[0]["checked"]
                    is_currently_checked = str(val).lower() in ["true", "1", "yes"]
            if is_currently_checked:
                checked_count += 1

    page_unit = 2
    total_target_pages = total_items_count * page_unit
    done_total_pages = checked_count * page_unit
    remaining_total_pages = max(0, total_target_pages - done_total_pages)
    daily_target = round(remaining_total_pages / remaining_days, 1)
    
    school_target_pages = max(0, school_p - s_p + 1)
    done_round1_pages = min(pages_per_round * page_unit, done_total_pages)
    catchup_diff = done_round1_pages - school_target_pages
    
    is_safe = catchup_diff >= 0
    catchup_status_text = "完了・余裕あり" if is_safe else f"あと {-catchup_diff}P遅れ"
    
    completion_rate = round((checked_count / total_items_count * 100), 1) if total_items_count > 0 else 0.0

    updated_rows.append({
        "教科": subj,
        "範囲": f"p.{s_p} 〜 p.{e_p}",
        "学校進度": f"~p.{school_p}",
        "目標": f"{t_round}周",
        "完了区切り数": checked_count,
        "総区切り数": total_items_count,
        "達成率(%)": completion_rate,
        "残りトータル(P)": remaining_total_pages,
        "1日ノルマ(P/日)": daily_target,
        "追いつき状況": catchup_status_text,
        "is_safe": is_safe
    })

result_df = pd.DataFrame(updated_rows)

# --- 画面モードごとの表示 ---
if app_mode == "📝 チェックリスト画面":
    st.subheader(f"🎯 教科別ページチェック（{test_stage}対策）")

    tabs = st.tabs([item["教科"] for item in subjects_config])
    
    for i, tab in enumerate(tabs):
        item = subjects_config[i]
        subj = item["教科"]
        s_p = subject_settings[subj]["start"]
        e_p = subject_settings[subj]["end"]
        school_p = subject_settings[subj]["school_progress"]
        t_round = subject_settings[subj]["target_round"]
        
        page_blocks = []
        current = s_p
        while current <= e_p:
            next_p = min(current + 1, e_p)
            page_blocks.append((current, next_p))
            current += 2
            
        with tab:
            st.markdown(f"### 📖 {subj} （{test_stage}）")
            st.markdown(f"📌 **範囲:** p.{s_p} 〜 p.{e_p} ｜ 🏫 **学校の授業進度:** ~p.{school_p} まで ｜ 🎯 **目標:** {t_round}周")
            st.write("やったページをポチポチチェック 👇")
            
            checked_count_tab = 0
            for r in range(1, t_round + 1):
                if t_round > 1:
                    st.markdown(f"**🔹 【 {r}周目 】**")
                
                cols_grid = st.columns(5)
                for idx, (p_start, p_end) in enumerate(page_blocks):
                    col_target = cols_grid[idx % 5]
                    with col_target:
                        label_text = f"〜p.{p_end}"
                        
                        is_currently_checked = False
                        if not df_db.empty and all(col in df_db.columns for col in ["test_stage", "subject", "round", "page", "checked"]):
                            matched = df_db[(df_db["test_stage"].astype(str) == str(test_stage)) & 
                                            (df_db["subject"].astype(str) == str(subj)) & 
                                            (df_db["round"].astype(str) == str(r)) & 
                                            (df_db["page"].astype(str) == str(p_end))]
                            if not matched.empty:
                                val = matched.iloc[0]["checked"]
                                is_currently_checked = str(val).lower() in ["true", "1", "yes"]
                        
                        chk_key = f"chk_{test_stage}_{subj}_r{r}_p{p_start}"
                        is_checked = st.checkbox(label_text, value=is_currently_checked, key=chk_key)
                        
                        if is_checked:
                            checked_count_tab += 1
                            
                        if is_checked != is_currently_checked:
                            try:
                                payload = {
                                    "action": "save",
                                    "test_stage": test_stage,
                                    "subject": subj,
                                    "round": r,
                                    "page": p_end,
                                    "checked": is_checked
                                }
                                requests.post(GAS_URL, json=payload)
                                st.cache_data.clear()
                            except Exception as err:
                                st.error(f"保存エラー: {err}")

            total_items_count = len(page_blocks) * t_round
            goal_progress_ratio = checked_count_tab / total_items_count if total_items_count > 0 else 0.0
            
            st.markdown("---")
            st.write(f"🏆 **【{test_stage} 目標ゴールへの進捗】** ({checked_count_tab} / {total_items_count} 区切り完了)")
            st.progress(goal_progress_ratio)

    # 風船演出
    all_caught_up = all(result_df["is_safe"])
    all_completed = all(result_df["完了区切り数"] >= result_df["総区切り数"])
    if len(result_df) > 0 and all_caught_up and not all_completed:
        st.balloons()
        st.success("🎈 すばらしい！本日のノルマをしっかり達成しました！この調子で頑張ろう！🎉")

else:
    # --- 🖨️ サマリー・進捗一覧印刷画面（A4収まり最適化） ---
    st.markdown('<div class="print-container">', unsafe_allow_html=True)
    
    st.header(f"🖨️ {test_stage} ノルマ・達成度進捗サマリー")
    st.caption("この画面をそのまま印刷（Ctrl + P または Cmd + P）してA4 1枚でご利用いただけます。")
    
    st.divider()

    st.subheader("🎯 本日のノルマ・進度サマリー")
    
    cols = st.columns(3)
    for i, row in result_df.iterrows():
        col_target = cols[i % 3]
        subj_name = row["教科"]
        daily_val = row["1日ノルマ(P/日)"]
        left_p = row["残りトータル(P)"]
        target_str = row["目標"]
        status_text = row["追いつき状況"]
        is_safe = row["is_safe"]
        
        delta_text = f"残り {left_p}P ({target_str})" if left_p > 0 else "コンプリート！🎉"
        
        if is_safe:
            status_html = f"<span style='color: #09ab3b; font-weight: bold;'>✔ {status_text}</span>"
        else:
            status_html = f"<span style='color: #e65100; font-weight: bold;'>▲ {status_text}</span>"
        
        with col_target:
            st.markdown(f"""
            <div style="padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; background-color: #fff; margin-bottom: 8px;">
                <div style="font-size: 0.85rem; color: #444; font-weight: bold;">{subj_name}</div>
                <div style="font-size: 1.2rem; font-weight: bold; color: #111; margin: 2px 0;">{daily_val} P/日</div>
                <div style="font-size: 0.75rem;">{status_html}</div>
                <div style="font-size: 0.75rem; color: #555; margin-top: 1px;">{delta_text}</div>
            </div>
            """, unsafe_allow_html=True)

    st.subheader("📊 教科別 達成率グラフ")
    chart_data = result_df.set_index("教科")[["達成率(%)"]]
    st.bar_chart(chart_data, color="#4CAF50", height=180)

    st.subheader("📋 進捗一覧テーブル")
    st.dataframe(result_df[["教科", "範囲", "学校進度", "目標", "完了区切り数", "総区切り数", "達成率(%)", "残りトータル(P)", "1日ノルマ(P/日)", "追いつき状況"]], use_container_width=True, height=220)

    st.markdown('</div>', unsafe_allow_html=True)
