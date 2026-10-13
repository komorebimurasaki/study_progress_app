import streamlit as st
import pandas as pd
from datetime import datetime, date

st.set_page_config(page_title="定期テスト ポチポチ進捗＆ノルマ管理アプリ", layout="wide")

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
st.write("✨ メイン画面で終わったページをポチポチチェックして、テストに向けて進もう！")

# 初期データの設定（教科、デフォルトの開始ページ、末ページ、目標周回数）
subjects_config = [
    {"教科": "国語", "開始": 1, "末尾": 39, "目標周回": 1},
    {"教科": "数学", "開始": 1, "末尾": 37, "目標周回": 1},
    {"教科": "英語", "開始": 1, "末尾": 31, "目標周回": 1},
    {"教科": "理科", "開始": 1, "末尾": 34, "目標周回": 1},
    {"教科": "地理", "開始": 1, "末尾": 25, "目標周回": 1},
    {"教科": "歴史", "開始": 1, "末尾": 13, "目標周回": 1},
]

# --- 1. サイドバー：ワークの範囲と目標の設定（最初に設定するもの） ---
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
st.sidebar.caption("※最初にここを設定したら、日々のチェックはメイン画面で行います。")

subject_settings = {}
for item in subjects_config:
    subj = item["教科"]
    st.sidebar.markdown(f"--- **{subj}** ---")
    
    col_s, col_e = st.sidebar.columns(2)
    with col_s:
        start_p = st.number_input(f"{subj} 開始P", min_value=1, max_value=300, value=item["開始"], key=f"start_{subj}")
    with col_e:
        end_p = st.number_input(f"{subj} 末尾P", min_value=1, max_value=300, value=item["末尾"], key=f"end_{subj}")
    
    target_round = st.sidebar.selectbox(f"{subj} の目標周回", options=[1, 2, 3], index=item["目標周回"]-1, key=f"target_round_{subj}")
    
    subject_settings[subj] = {
        "start": start_p,
        "end": end_p,
        "target_round": target_round
    }

# --- 2. メイン画面：ポチポチチェック ＆ グラフ（プログレスバー） ---
st.subheader("🎯 教科別ページチェック（ポチポチ進捗）")
st.caption("タブから教科を選び、終わった「奇数ページ（2ページで1区切り）」にポチポチチェックを入れていきましょう！")

tabs = st.tabs([item["教科"] for item in subjects_config])
updated_rows = []

for i, tab in enumerate(tabs):
    item = subjects_config[i]
    subj = item["教科"]
    s_p = subject_settings[subj]["start"]
    e_p = subject_settings[subj]["end"]
    t_round = subject_settings[subj]["target_round"]
    
    # 1周分の奇数ページリストを作成（例: 1, 3, 5, 7, ...）
    odd_pages = list(range(s_p, e_p + 1, 2))
    pages_per_round = len(odd_pages)
    
    with tab:
        st.markdown(f"### 📖 {subj} （範囲: p.{s_p} 〜 p.{e_p} / 目標: {t_round}周）")
        
        # 複数周する場合の全チェック項目を作成（例: 1周目[1,3,5...], 2周目[1,3,5...] など）
        all_check_items = []
        for r in range(1, t_round + 1):
            for p in odd_pages:
                all_check_items.append((r, p))
        
        total_items_count = len(all_check_items)
        
        st.write("やったページをポチポチチェック 👇")
        
        # 周ごとにチェックボックスを整理して配置
        checked_count = 0
        for r in range(1, t_round + 1):
            if t_round > 1:
                st.markdown(f"**🔹 【 {r}周目 】**")
            
            cols_grid = st.columns(5)
            for idx, p in enumerate(odd_pages):
                col_target = cols_grid[idx % 5]
                with col_target:
                    # チェックの状態を保持するキー
                    chk_key = f"chk_{subj}_r{r}_p{p}"
                    is_checked = st.checkbox(f"p.{p}〜", key=chk_key)
                    if is_checked:
                        checked_count += 1
                        
        # グラフ（プログレスバー）用の進捗率計算
        progress_ratio = checked_count / total_items_count if total_items_count > 0 else 0.0
        
        st.markdown("---")
        st.write(f"📊 **{subj} の達成状況:** {checked_count} / {total_items_count} 区切り完了")
        st.progress(progress_ratio)
        
        # ページ数・ノルマ換算（1区切り ＝ 2ページ分として計算）
        page_unit = 2
        total_target_pages = total_items_count * page_unit
        done_total_pages = checked_count * page_unit
        remaining_total_pages = max(0, total_target_pages - done_total_pages)
        daily_target = round(remaining_total_pages / remaining_days, 1)
        
        updated_rows.append({
            "教科": subj,
            "範囲": f"p.{s_p} 〜 p.{e_p}",
            "目標": f"{t_round}周",
            "完了数": f"{checked_count} / {total_items_count} 区切り",
            "残りトータル(P)": remaining_total_pages,
            "1日ノルマ(P/日)": daily_target,
            "_done_total": done_total_pages,
            "_target_total": total_target_pages
        })

result_df = pd.DataFrame(updated_rows)

st.divider()

# --- 3. 本日のノルマまとめ＆一覧表示 ---
st.subheader("🎯 本日のノルマサマリー")
st.caption(f"テスト予定日まで あと {remaining_days} 日")

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
