import streamlit as st
import pandas as pd
from datetime import datetime, date

st.set_page_config(page_title="期末テスト対策 3周マスターアプリ", layout="wide")
st.title("📚 期末テスト対策！ワークブック3周進捗＆ノルマ管理アプリ")

# 初期データ（教科、これまでの総ページ数、終わったページ、現在の周回数）
initial_data = [
    {"教科": "国語", "総ページ数": 39, "終わったページ": 8, "現在の周回": 1},
    {"教科": "数学", "総ページ数": 37, "終わったページ": 28, "現在の周回": 1},
    {"教科": "英語", "総ページ数": 31, "終わったページ": 21, "現在の周回": 1},
    {"教科": "理科", "総ページ数": 34, "終わったページ": 31, "現在の周回": 1},
    {"教科": "地理", "総ページ数": 25, "終わったページ": 9, "現在の周回": 1},
    {"教科": "歴史", "総ページ数": 13, "終わったページ": 7, "現在の周回": 1},
]

df = pd.DataFrame(initial_data)

# --- 1. サイドバー：期限と「総ページ数・進捗」の更新 ---
st.sidebar.header("🗓️ テスト日・期限の設定")
target_date = st.sidebar.date_input("期末テスト予定日", date.today())
today = date.today()
remaining_days = (target_date - today).days

if remaining_days <= 0:
    remaining_days = 1
    st.sidebar.warning("⚠️ 予定日が本日以前になっています。")
else:
    st.sidebar.info(f"⏳ テストまで **あと {remaining_days} 日** です！")

st.sidebar.divider()
st.sidebar.subheader("✏️ 授業の進み具合 ＆ 周回数の更新")
st.sidebar.caption("※授業が進んで総ページ数が増えたり、2周目・3周目に入る時にここで調整できます。")

updated_rows = []

for idx, row in df.iterrows():
    st.sidebar.markdown(f"--- **{row['教科']}** ---")
    
    # 総ページ数が増えることに対応
    new_total_pages = st.sidebar.number_input(
        f"{row['教科']} の現在の総ページ数", 
        min_value=1, max_value=200, 
        value=int(row['総ページ数']),
        key=f"total_{row['教科']}"
    )
    
    # 何周目か
    round_num = st.sidebar.selectbox(
        f"{row['教科']} の挑戦中の周回", 
        options=[1, 2, 3], 
        index=int(row['現在の周回'])-1,
        key=f"round_{row['教科']}"
    )
    
    # 終わったページ
    current_done = st.sidebar.number_input(
        f"{row['教科']} の今周で終わったページ", 
        min_value=0, 
        max_value=int(new_total_pages), 
        value=min(int(row['終わったページ']), int(new_total_pages)),
        key=f"done_{row['教科']}"
    )
    
    # 3周トータルでの計算ロジック
    target_3rounds = new_total_pages * 3
    done_3rounds = (new_total_pages * (round_num - 1)) + current_done
    remaining_3rounds = max(0, target_3rounds - done_3rounds)
    
    # 1日あたりのノルマ（3周完了までの残りページ ÷ 残り日数）
    daily_target = round(remaining_3rounds / remaining_days, 1)
    
    updated_rows.append({
        "教科": row["教科"],
        "現在の周回": f"{round_num}周目",
        "総ページ(1周分)": new_total_pages,
        "今周の終了(P)": current_done,
        "3周トータル残(P)": remaining_3rounds,
        "1日ノルマ(P/日)": daily_target
    })

result_df = pd.DataFrame(updated_rows)

# --- 2. メイン画面：1日ノルマの可視化（3周完了に向けた自動計算） ---
st.subheader("🎯 3周クリアに向けた「今日の1日ノルマ」")
st.caption(f"問題集を3周やり切るために、テスト直前まで（あと {remaining_days} 日）に1日あたり進めるべき目安です。")

cols = st.columns(len(result_df))
for i, col in enumerate(cols):
    row = result_df.iloc[i]
    left_p = row['3周トータル残(P)']
    
    if left_p > 0:
        delta_text = f"3周トータル残り {left_p} ページ"
    else:
        delta_text = "3周コンプリート！🎉"
        
    col.metric(
        label=row["教科"], 
        value=f"{row['1日ノルマ(P/日)']} ページ/日",
        delta=delta_text
    )

st.divider()

# --- 3. 詳細な進捗テーブル ---
st.subheader("📊 教科別 3周チャレンジ状況一覧")
st.dataframe(result_df, use_container_width=True)

# 全体の進捗（3周ベース）の安全な計算
total_target_all = (result_df["総ページ(1周分)"].sum()) * 3
total_done_calc = sum([
    (int(r["現在の周回"].replace("周目", "")) - 1) * r["総ページ(1周分)"] + r["今周の終了(P)"] 
    for _, r in result_df.iterrows()
])
overall_progress = min(1.0, total_done_calc / total_target_all) if total_target_all > 0 else 0

st.subheader("🏆 3周マスター達成度")
st.progress(overall_progress, text=f"3周トータル進捗: {total_done_calc} / {total_target_all} ページ完了")