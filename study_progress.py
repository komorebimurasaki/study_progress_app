import streamlit as st
import pandas as pd
from datetime import datetime, date

st.set_page_config(page_title="定期テスト 計画＆進捗管理アプリ", layout="wide")

# --- 🖨️ 印刷時の見た目をキレイにするためのCSS設定 ---
st.markdown("""
<style>
@media print {
    /* 印刷時にサイドバーやStreamlitの余計なメニューを隠す */
    [data-testid="stSidebar"] {
        display: none;
    }
    header, footer, .stActionButton {
        visibility: hidden;
    }
    /* メインエリアを全幅で綺麗に見せる */
    .main {
        width: 100% !important;
    }
}
</style>
""", unsafe_allow_html=True)

st.title("📚 定期テスト 計画＆進捗管理アプリ")

# 初期データ（教科、開始ページ、末ページ、終わったページ、現在の周回数、目標周回数）
initial_data = [
    {"教科": "国語", "開始ページ": 1, "末ページ": 39, "終わったページ": 8, "現在の周回": 1, "目標周回": 2},
    {"教科": "数学", "開始ページ": 1, "末ページ": 37, "終わったページ": 28, "現在の周回": 1, "目標周回": 2},
    {"教科": "英語", "開始ページ": 1, "末ページ": 31, "終わったページ": 21, "現在の周回": 1, "目標周回": 2},
    {"教科": "理科", "開始ページ": 1, "末ページ": 34, "終わったページ": 31, "現在の周回": 1, "目標周回": 2},
    {"教科": "地理", "開始ページ": 1, "末ページ": 25, "終わったページ": 9, "現在の周回": 1, "目標周回": 2},
    {"教科": "歴史", "開始ページ": 1, "末ページ": 13, "終わったページ": 7, "現在の周回": 1, "目標周回": 2},
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
st.sidebar.subheader("✏️ ワークの範囲 ＆ 周回数の設定")
st.sidebar.caption("※「p.10からp.35まで」のように、開始と終わりのページを入力できます。")

updated_rows = []

for idx, row in df.iterrows():
    st.sidebar.markdown(f"--- **{row['教科']}** ---")
    
    # 1. 開始ページと末ページの入力
    col_s, col_e = st.sidebar.columns(2)
    with col_s:
        start_p = st.number_input(
            f"{row['教科']} 開始P", 
            min_value=1, max_value=300, 
            value=int(row['開始ページ']),
            key=f"start_{row['教科']}"
        )
    with col_e:
        end_p = st.number_input(
            f"{row['教科']} 末尾P", 
            min_value=1, max_value=300, 
            value=int(row['末ページ']),
            key=f"end_{row['教科']}"
        )
    
    # 1周あたりの総ページ数を自動計算
    pages_per_round = max(1, end_p - start_p + 1)
    
    # 2. 目標周回数の選択
    target_round = st.sidebar.selectbox(
        f"{row['教科']} の目標周回数", 
        options=[1, 2, 3], 
        index=int(row['目標周回'])-1,
        key=f"target_round_{row['教科']}"
    )
    
    # 3. 現在挑戦中の周回
    round_num = st.sidebar.selectbox(
        f"{row['教科']} の現在の周回", 
        options=list(range(1, target_round + 1)), 
        index=min(int(row['現在の周回'])-1, target_round-1),
        key=f"round_{row['教科']}"
    )
    
    # 4. 今周で終わったページ数
    current_done = st.sidebar.number_input(
        f"{row['教科']} の今周の完了P数", 
        min_value=0, 
        max_value=int(pages_per_round), 
        value=min(int(row['終わったページ']), int(pages_per_round)),
        key=f"done_{row['教科']}"
    )
    
    # 計算ロジック
    total_target_pages = pages_per_round * target_round
    done_total_pages = (pages_per_round * (round_num - 1)) + current_done
    remaining_total_pages = max(0, total_target_pages - done_total_pages)
    
    # 1日あたりのノルマ
    daily_target = round(remaining_total_pages / remaining_days, 1)
    
    updated_rows.append({
        "教科": row["教科"],
        "範囲": f"p.{start_p} 〜 p.{end_p} (全{pages_per_round}P)",
        "目標": f"{target_round}周",
        "現在の周回": f"{round_num}周目",
        "今周の終了(P)": current_done,
        "残りトータル(P)": remaining_total_pages,
        "1日ノルマ(P/日)": daily_target,
        # 内部計算用
        "_pages_per_round": pages_per_round,
        "_target_round": target_round,
        "_done_total": done_total_pages
    })

result_df = pd.DataFrame(updated_rows)

# --- 2. メイン画面：1日ノルマの可視化 ---
st.subheader("🎯 目標クリアに向けた今日の1日ノルマ")
st.caption(f"テスト直前まで（あと {remaining_days} 日）に、科目ごとに設定した目標（1〜3周）を達成するための目安です。")

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

st.divider()

# --- 3. 詳細な進捗テーブル ---
st.subheader("📊 教科別 進捗・残り状況一覧")
display_df = result_df[["教科", "範囲", "目標", "現在の周回", "今周の終了(P)", "残りトータル(P)", "1日ノルマ(P/日)"]]
st.dataframe(display_df, use_container_width=True)

# 全体の進捗の計算
total_target_all = sum([r["_pages_per_round"] * r["_target_round"] for _, r in result_df.iterrows()])
total_done_calc = sum([r["_done_total"] for _, r in result_df.iterrows()])
overall_progress = min(1.0, total_done_calc / total_target_all) if total_target_all > 0 else 0

st.subheader("🏆 全体目標達成度")
st.progress(overall_progress, text=f"トータル進捗: {total_done_calc} / {total_target_all} ページ完了")
