import streamlit as st
import pandas as pd
from datetime import datetime, date

st.set_page_config(page_title="定期テスト 計画＆進捗管理アプリ", layout="wide")

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

st.title("📚 定期テスト ポチポチ進捗＆ノルマ管理アプリ")
st.write("✨ ワークの「奇数ページ（2ページで1区切り）」ごとにポチポチチェックして、進捗を体感しよう！")

# 初期データの設定（教科、開始ページ、末ページ、目標周回数）
# 各科目の「完了した奇数ページ番号のリスト」を管理します
initial_data = [
    {"教科": "国語", "開始ページ": 1, "末ページ": 39, "目標周回": 2, "完了ページリスト": [1, 3, 5, 7]},
    {"教科": "数学", "開始ページ": 1, "末ページ": 37, "目標周回": 2, "完了ページリスト": [1, 3, 5, 7, 9, 11, 13, 15]},
    {"教科": "英語", "開始ページ": 1, "末ページ": 31, "目標周回": 2, "完了ページリスト": [1, 3, 5, 7, 9]},
    {"教科": "理科", "開始ページ": 1, "末ページ": 34, "目標周回": 2, "完了ページリスト": [1, 3, 5, 7, 9, 11]},
    {"教科": "地理", "開始ページ": 1, "末ページ": 25, "目標周回": 2, "完了ページリスト": [1, 3, 5]},
    {"教科": "歴史", "開始ページ": 1, "末ページ": 13, "目標周回": 2, "完了ページリスト": [1, 3]},
]

df = pd.DataFrame(initial_data)

# --- 1. サイドバー：テスト日と各科目の設定 ---
st.sidebar.header("🗓️ テスト日・期限の設定")
target_date = st.sidebar.date_input("テスト予定日", date.today())
today = date.today()
remaining_days = (target_date - today).days

if remaining_days <= 0:
    remaining_days = 1
    st.sidebar.warning("⚠️ 予定日が本日以前になっています。")
else:
    st.sidebar.info(f"⏳ テストまで **あと {remaining_days} 日** です！")

st.sidebar.divider()
st.sidebar.subheader("✏️ ワークの範囲 ＆ 目標設定")

subject_settings = {}
for idx, row in df.iterrows():
    st.sidebar.markdown(f"--- **{row['教科']}** ---")
    
    col_s, col_e = st.sidebar.columns(2)
    with col_s:
        start_p = st.number_input(f"{row['教科']} 開始P", min_value=1, max_value=300, value=int(row['开始ページ'] if '开始ページ' in row else row['開始ページ']), key=f"start_{row['教科']}")
    with col_e:
        end_p = st.number_input(f"{row['教科']} 末尾P", min_value=1, max_value=300, value=int(row['末ページ']), key=f"end_{row['教科']}")
    
    target_round = st.sidebar.selectbox(f"{row['教科']} の目標周回", options=[1, 2, 3], index=int(row['目標周回'])-1, key=f"target_round_{row['教科']}")
    
    subject_settings[row['教科']] = {
        "start": start_p,
        "end": end_p,
        "target_round": target_round
    }

st.sidebar.divider()
st.sidebar.info("💡 メイン画面のタブから教科を選んで、終わったページをポチポチチェックしていこう！")

# --- 2. メイン画面：タブ切り替えによる「ポチポチ式」ページチェック ---
st.subheader("🎯 教科別ページチェック（ポチポチ進捗）")
st.caption("終わった「奇数ページ（区切りの始まり）」にチェックを入れていくと、進捗と1日ノルマが自動で連動します！")

tabs = st.tabs([row["教科"] for row in initial_data])

updated_rows = []

for i, tab in enumerate(tabs):
    row = initial_data[i]
    subj = row["教科"]
    s_p = subject_settings[subj]["start"]
    e_p = subject_settings[subj]["end"]
    t_round = subject_settings[subj]["target_round"]
    
    # 1周分の奇数ページリストを作成（例: 1, 3, 5, 7, ...）
    odd_pages = list(range(s_p, e_p + 1, 2))
    pages_per_round = len(odd_pages)
    
    with tab:
        st.markdown(f"### 📖 {subj} （範囲: p.{s_p} 〜 p.{e_p} / 目標: {t_round}周）")
        st.write("やったページをポチポチチェックしてください 👇")
        
        # チェックボックスを綺麗に並べる（5列グリッド）
        checked_pages = []
        cols_grid = st.columns(5)
        
        for idx, p in enumerate(odd_pages):
            # デフォルトですでに終わっているページ判定
            default_val = p in row["完了ページリスト"]
            col_target = cols_grid[idx % 5]
            
            with col_target:
                is_checked = st.checkbox(f"p.{p}〜", value=default_val, key=f"chk_{subj}_{p}")
                if is_checked:
                    checked_pages.append(p)
        
        # 周回ごとの進捗を計算（何周目まで完了しているか、今何周目か）
        total_checked_count = len(checked_pages)
        current_round = min(t_round, (total_checked_count // pages_per_round) + 1)
        current_round_done_count = total_checked_count % pages_per_round
        if total_checked_count > 0 and current_round_done_count == 0 and total_checked_count >= pages_per_round:
            current_round = min(t_round, total_checked_count // pages_per_round)
            current_round_done_count = pages_per_round if current_round == t_round else 0
            
        # 3周トータルでの残ページ計算（奇数ページ数をページ数に換算する場合は 1区切り=2ページ分 または 1ブロック単位で計算）
        # ここでは「1奇数ページ ＝ 2ページ分（見開き1区切り）」としてページ数換算します
        page_unit = 2 
        total_target_pages = (pages_per_round * page_unit) * t_round
        done_total_pages = total_checked_count * page_unit
        remaining_total_pages = max(0, total_target_pages - done_total_pages)
        
        daily_target = round(remaining_total_pages / remaining_days, 1)
        
        updated_rows.append({
            "教科": subj,
            "範囲": f"p.{s_p} 〜 p.{e_p}",
            "目標": f"{t_round}周",
            "完了数": f"{total_checked_count} / {pages_per_round * t_round} 区切り",
            "残りトータル(P)": remaining_total_pages,
            "1日ノルマ(P/日)": daily_target,
            "_done_total": done_total_pages,
            "_target_total": total_target_pages
        })

result_df = pd.DataFrame(updated_rows)

st.divider()

# --- 3. 今日のノルマまとめ＆一覧表示 ---
st.subheader("📊 本日のノルマ＆全体進捗サマリー")

cols = st.columns(len(result_df))
for i, col in enumerate(cols):
    row = result_df.iloc[i]
    left_p = row['残りトータル(P)']
    
    if left_p > 0:
        delta_text = f"残り {left_p} ページ"
    else:
        delta_text = "目標コンプリート！🎉"
        
    col.metric(
        label=row["教科"], 
        value=f"{row['1日ノルマ(P/日)']} ページ/日",
        delta=delta_text
    )

st.subheader("📋 進捗一覧テーブル")
display_df = result_df[["教科", "範囲", "目標", "完了数", "残りトータル(P)", "1日ノルマ(P/日)"]]
st.dataframe(display_df, use_container_width=True)

# 全体の進捗バー
total_target_all = sum([r["_target_total"] for _, r in result_df.iterrows()])
total_done_all = sum([r["_done_total"] for _, r in result_df.iterrows()])
overall_progress = min(1.0, total_done_all / total_target_all) if total_target_all > 0 else 0

st.subheader("🏆 全体目標達成度")
st.progress(overall_progress, text=f"トータル進捗: {total_done_all} / {total_target_all} ページ完了")
