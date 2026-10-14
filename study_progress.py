import streamlit as st
import pandas as pd
from datetime import datetime, date
import requests
import json
import random
import altair as alt

st.set_page_config(page_title="定期テスト 計画＆進捗管理アプリ", layout="wide")

# --- 🔌 GAS（ウェブアプリ）のURL設定 ---
GAS_URL = "https://script.google.com/macros/s/AKfycbzJ4haEJBc8IYQSS4Hc9PG3tMVQLGPd9VjJtu55UBSaKJJQ18dJFabjPBXL4Fu1H2I/exec"

# --- 🖨️ 印刷時のスタイル・A4収まり設定 ---
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
    body {
        zoom: 65%;
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

# --- 1. サイドバー：初期ページを「期末テストの印刷・サマリー画面」に設定 ---
st.sidebar.header("🖥️ 表示モード切替")
app_mode = st.sidebar.radio(
    "表示する画面を選択", 
    options=["🖨️ サマリー・進捗一覧印刷画面", "📝 チェックリスト画面"], 
    key="selected_app_mode"
)

st.sidebar.divider()

st.sidebar.header("🗓️ テスト段階・期限の設定")
# 初期選択を「期末テスト」に設定
test_stage = st.sidebar.radio("管理するテストを選択", options=["期末テスト", "中間テスト"], key="selected_test_stage")

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

# --- 2. スプレッドシートからのチェックデータ読み込み（中間・期末でデータ共有） ---
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
                # どちらのテストでチェックしていても共通でカウントする
                matched = df_db[(df_db["subject"].astype(str) == str(subj)) & 
                                (df_db["round"].astype(str) == str(r)) & 
                                (df_db["page"].astype(str) == str(p_end)) &
                                (df_db["checked"].astype(str).str.lower().isin(["true", "1", "yes"]))]
                if not matched.empty:
                    is_currently_checked = True
            if is_currently_checked:
                checked_count += 1

    page_unit = 2
    total_target_pages = total_items_count * page_unit
    done_total_pages = checked_count * page_unit
    remaining_total_pages = max(0, total_target_pages - done_total_pages)
    daily_target = round(remaining_total_pages / remaining_days, 1)
    
    school_target_pages = max(0, school_p - s_p + 1)
    done_round1_pages = min(pages_per_round * page_unit, checked_count * page_unit)
    
    # 1周目が学校の授業進度まで進んだかどうかの判定
    round1_blocks_count = len([b for b in page_blocks if b[1] <= school_p])
    round1_checked_in_school = 0 # 1周目で学校進度までにチェックが入っている数
    
    # ペース指標
    if daily_target <= 1.0:
        pace_status = "✅ 余裕あり"
        pace_color = "#09ab3b"
    elif daily_target <= 1.3:
        pace_status = "👍 順調"
        pace_color = "#2196F3"
    else:
        pace_status = "🔥 がんばれ"
        pace_color = "#e65100"

    completion_rate = round((checked_count / total_items_count * 100), 1) if total_items_count > 0 else 0.0

    updated_rows.append({
        "教科": subj,
        "範囲": f"p.{s_p} 〜 p.{e_p}",
        "学校進度": f"~p.{school_p}",
        "目標": f"{t_round}周",
        "完了区切り数": checked_count,
        "総区切り数": total_items_count,
        "達成率(%)": round(completion_rate, 1),
        "残りトータル(P)": round(remaining_total_pages, 1),
        "1日ノルマ(P/日)": round(daily_target, 1),
        "ペース指標": pace_status,
        "pace_color": pace_color,
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
            
            # 1周目が学校進度まで進んだ場合の誘導メッセージ
            s_row = result_df[result_df["教科"] == subj].iloc[0]
            # 1周目の中で学校進度までのページが完了しているか簡易判定
            school_blocks = [b for b in page_blocks if b[1] <= school_p]
            school_completed = True
            if school_blocks:
                for b_start, b_end in school_blocks:
                    matched = df_db[(df_db["subject"].astype(str) == str(subj)) & 
                                    (df_db["round"].astype(str) == "1") & 
                                    (df_db["page"].astype(str) == str(b_end)) &
                                    (df_db["checked"].astype(str).str.lower().isin(["true", "1", "yes"]))]
                    if matched.empty:
                        school_completed = False
                        break
            
            if school_completed and len(school_blocks) > 0:
                st.info(f"💡 **【ステップアップのチャンス！】** {subj}の1周目（学校の授業進度 p.{school_p}まで）が完了しました！次は**2周目**や**3周目**の復習に進んで定着させましょう！🚀")
            
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
                            matched = df_db[(df_db["subject"].astype(str) == str(subj)) & 
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

            # --- 各教科ごとの「今日の分を入力した！」ボタン ---
            if st.button(f"🎈 {subj} の今日の分を入力した！", key=f"btn_complete_{subj}"):
                st.balloons()
                st.success(f"🎉 {subj}の今日の学習お疲れ様でした！素晴らしい頑張りです！✨")

else:
    # --- 🖨️ サマリー・進捗一覧印刷画面（初期表示） ---
    st.markdown('<div class="print-container">', unsafe_allow_html=True)
    
    st.header(f"🖨️ {test_stage} ノルマ・達成度進捗サマリー")
    st.caption("この画面をそのまま印刷（Ctrl + P または Cmd + P）してA4 1枚でご利用いただけます。")
    
    st.divider()

    # --- 💡 ランダム励ましメッセージ機能 ---
    encouragement_quotes = [
        "えみちゃん、今日もお疲れさま！少しずつでも机に向かってるの、本当にえらい！",
        "一気にやらなくて大丈夫！まずは5分だけやってみよ〜👍",
        "中1の今頑張ってること、絶対に後から効いてくるよ！応援してる！",
        "今日の頑張りが未来の自分へのプレゼント！無理せずファイト〜✨",
        "集中切れたら一回深呼吸！マイペースでいこうね。",
        "部活もあって大変なのに、ちゃんと勉強もやろうとしててすごいよ！",
        "最初はみんな覚えること多くて大変な時期！ここを乗り越えたら一気に楽になるよ💪",
        "えみなら絶対できる！『できた！』を1つずつ増やしていこう！",
        "100点を目指さなくてOK！昨日の自分より1問多く解けたら大勝利だよ✨",
        "わからない問題があったら『伸びしろ発見！』って思っちゃおう！",
        "最近忙しそうだけど大丈夫？たまには甘いものでも食べて休憩してね ☕️",
        "疲れてるときは無理しすぎないでね。休むのも大事な勉強のうちだよ！",
        "『今日はここまで頑張った』って自分をいっぱい褒めてあげてね。",
        "焦らなくて大丈夫。自分のペースで1歩ずつ進んでいこうね☘️",
        "いつでも応援してるからね！困ったときはいつでも吐き出してOKだよ！",
        "テスト期間のラスボス感すごいけどえみなら余裕で倒せるはず！⚔️",
        "脳みそフル回転中だね！糖分補給して乗り切ろう〜！🍫",
        "勉強が終わったら美味しいもの（または好きなこと）が待ってるぞ〜！"
    ]

    col_msg1, col_msg2 = st.columns([3, 1])
    with col_msg1:
        if "current_quote" not in st.session_state:
            st.session_state["current_quote"] = random.choice(encouragement_quotes)
        st.info(f"💬 **今日の応援メッセージ:** \n\n {st.session_state['current_quote']}")
    with col_msg2:
        st.write("")
        if st.button("🔄 メッセージを替える"):
            st.session_state["current_quote"] = random.choice(encouragement_quotes)
            st.rerun()

    st.subheader("🎯 本日のノルマ・進度サマリー")
    
    cols = st.columns(3)
    for i, row in result_df.iterrows():
        col_target = cols[i % 3]
        subj_name = row["教科"]
        daily_val = row["1日ノルマ(P/日)"]
        left_p = row["残りトータル(P)"]
        target_str = row["目標"]
        pace_status = row["ペース指標"]
        pace_color = row["pace_color"]
        
        delta_text = f"残り {left_p}P ({target_str})" if left_p > 0 else "コンプリート！🎉"
        status_html = f"<span style='color: {pace_color}; font-weight: bold;'>{pace_status}</span>"
        
        with col_target:
            st.markdown(f"""
            <div style="padding: 4px 6px; border: 1px solid #ddd; border-radius: 4px; background-color: #fff; margin-bottom: 4px;">
                <div style="font-size: 0.7rem; color: #444; font-weight: bold;">{subj_name}</div>
                <div style="font-size: 0.95rem; font-weight: bold; color: #111; margin: 1px 0;">{daily_val} P/日</div>
                <div style="font-size: 0.6rem;">{status_html}</div>
                <div style="font-size: 0.6rem; color: #555; margin-top: 1px;">{delta_text}</div>
            </div>
            """, unsafe_allow_html=True)

    st.subheader("📊 教科別 達成率 (%) ＆ ペース連動カラー")
    
    chart = alt.Chart(result_df).mark_bar(size=22).encode(
        x=alt.X('教科:N', sort=None, title='', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('達成率(%):Q', title='達成率 (%)', scale=alt.Scale(nice=True, zero=True)),
        color=alt.Color('pace_color:N', scale=None),
        tooltip=['教科', '達成率(%)', 'ペース指標']
    ).properties(
        height=120
    )
    st.altair_chart(chart, use_container_width=True)

    st.subheader("📋 進捗一覧テーブル")
    display_df = result_df[["教科", "範囲", "学校進度", "目標", "完了区切り数", "総区切り数", "達成率(%)", "残りトータル(P)", "1日ノルマ(P/日)", "ペース指標"]].copy()
    display_df["達成率(%)"] = display_df["達成率(%)"].apply(lambda x: f"{x:.1f}")
    display_df["残りトータル(P)"] = display_df["残りトータル(P)"].apply(lambda x: f"{x:.1f}")
    display_df["1日ノルマ(P/日)"] = display_df["1日ノルマ(P/日)"].apply(lambda x: f"{x:.1f}")
    
    st.table(display_df)

    st.markdown('</div>', unsafe_allow_html=True)
