import streamlit as st
import pandas as pd
from datetime import datetime, date
import requests
import json

st.set_page_config(page_title="定期テスト 計画＆進捗管理アプリ", layout="wide")

# --- 🔌 GAS（ウェブアプリ）のURL設定 ---
GAS_URL = "https://script.google.com/macros/s/AKfycby18d2CsK58l_toJ7OYiK1Lp359j804g0O4uMmftybv6FgPTg8g08hG-AYXuUG3AeZQ/exec"

# --- 🖨️ 印刷時の見た目・切れ防止のためのCSS設定 ---
st.markdown("""
<style>
@media print {
    [data-testid="stSidebar"] {
        display: none !important;
    }
    header, footer, .stActionButton {
        display: none !important;
    }
    .main, .block-container {
        width: 100% !important;
        max-width: 100% !important;
        padding: 0 !important;
    }
}
</style>
""", unsafe_allow_html=True)

st.title("📚 定期テスト 計画＆進捗管理アプリ（完全クラウド同期）")
st.write("✨ テスト予定日・範囲・ポチポチ進捗のすべてがスプレッドシートに自動保存されます！")

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

# 設定を保存するヘルパー関数
def save_setting_to_gas(key, value):
    try:
        payload = {"action": "save_setting", "key": key, "value": str(value)}
        requests.post(GAS_URL, json=payload)
        st.cache_data.clear()
    except Exception as e:
        print(f"Setting save error: {e}")

# --- 1. サイドバー：テスト段階の選択 ＆ 基本設定 ---
st.sidebar.header("🗓️ テスト段階・期限の設定")
test_stage = st.sidebar.radio("管理するテストを選択", options=["中間テスト", "期末テスト"], key="selected_test_stage")

date_key = f"target_date_{test_stage}"
# スプレッドシートから日付を取得（なければ今日）
saved_date_str = db_settings.get(date_key)
if saved_date_str:
    try:
        default_date = datetime.strptime(saved_date_str[:10], "%Y-%m-%d").date()
    except:
        default_date = date.today()
else:
    default_date = date.today()

target_date = st.sidebar.date_input(f"{test_stage} 予定日", value=default_date, key=date_key)

# 日付が変更されたらスプレッドシートに保存
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
    default_end = item["中间末尾" if "中间末尾" in item else "中間末尾"] if test_stage == "中间テスト" or test_stage == "中間テスト" else item["期末末尾"]
    
    end_key = f"end_p_{test_stage}_{subj}"
    school_key = f"school_p_{test_stage}_{subj}"
    round_key = f"round_{test_stage}_{subj}"
    
    # 読み込み（DBになければデフォルト値）
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

# --- 3. メイン画面：ポチポチチェック ＆ 進捗管理 ---
st.subheader(f"🎯 教科別ページチェック（{test_stage}対策）")
st.caption(f"タブから教科を選び、終わった区切りにチェックを入れましょう。設定もポチポチもすべてスプレッドシートに保存されます！")

tabs = st.tabs([item["教科"] for item in subjects_config])
updated_rows = []

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
        
    pages_per_round = len(page_blocks)
    total_items_count = pages_per_round * t_round
    
    with tab:
        st.markdown(f"### 📖 {subj} （{test_stage}）")
        st.markdown(f"📌 **範囲:** p.{s_p} 〜 p.{e_p} ｜ 🏫 **学校の授業進度:** ~p.{school_p} まで ｜ 🎯 **目標:** {t_round}周")
        st.write("やったページをポチポチチェック 👇")
        
        checked_count = 0
        
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
                        checked_count += 1
                        
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

        # --- 計算処理 ---
        page_unit = 2
        total_target_pages = total_items_count * page_unit
        done_total_pages = checked_count * page_unit
        remaining_total_pages = max(0, total_target_pages - done_total_pages)
        daily_target = round(remaining_total_pages / remaining_days, 1)
        
        school_target_pages = max(0, school_p - s_p + 1)
        done_round1_pages = min(pages_per_round * page_unit, done_total_pages)
        catchup_diff = done_round1_pages - school_target_pages
        
        goal_progress_ratio = checked_count / total_items_count if total_items_count > 0 else 0.0
        
        st.markdown("---")
        st.write(f"🏆 **【{test_stage} 目標ゴールへの進捗】** ({checked_count} / {total_items_count} 区切り完了)")
        st.progress(goal_progress_ratio)
        
        if catchup_diff >= 0:
            st.success(f"✅ **【授業進度への追いつき】** 習った範囲（~p.{school_p}）に対して、十分完了しています！")
        else:
            st.warning(f"⚠️ **【授業進度への追いつき】** 現在の授業進度（~p.{school_p}）に対して、あと **{abs(catchup_diff)}ページ分** 追いつく必要があります！")
        
        updated_rows.append({
            "教科": subj,
            "範囲": f"p.{s_p} 〜 p.{e_p}",
            "学校進度": f"~p.{school_p}",
            "目標": f"{t_round}周",
            "残りトータル(P)": remaining_total_pages,
            "1日ノルマ(P/日)": daily_target,
            "追いつき状況": "完了・余裕あり" if catchup_diff >= 0 else f"あと {-catchup_diff}P遅れ",
            "_done_total": done_total_pages,
            "_target_total": total_target_pages
        })

result_df = pd.DataFrame(updated_rows)

st.divider()

# --- 4. サマリーと一覧表示 ---
st.subheader(f"🎯 本日のノルマ・進度サマリー（{test_stage}）")
cols = st.columns(len(result_df))
for i, col in enumerate(cols):
    row = result_df.iloc[i]
    left_p = row['残りトータル(P)']
    status = row['追いつき状況']
    delta_text = f"残り {left_p}P ({row['目標']})" if left_p > 0 else "目標コンプリート！🎉"
    col.metric(label=row["教科"], value=f"{row['1日ノルマ(P/日)']} ページ/日", delta=f"{status} / {delta_text}")

st.subheader("📋 進捗一覧テーブル")
st.dataframe(result_df[["教科", "範囲", "学校進度", "目標", "残りトータル(P)", "1日ノルマ(P/日)", "追いつき状況"]], use_container_width=True)
