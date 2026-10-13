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

st.title("📚 定期テスト 計画＆進捗管理アプリ")
st.write("✨ 「3周ゴールからの逆算ノルマ」と「いま授業で習っているところへの追いつき度」をダブルで可視化！")

# 初期データの設定（教科、デフォルトの開始、末尾、目標周回、現在の授業進度）
subjects_config = [
    {"教科": "国語", "開始": 1, "末尾": 39, "目標周回": 3, "授業進度": 25},
    {"教科": "数学", "開始": 1, "末尾": 37, "目標周回": 3, "授業進度": 30},
    {"教科": "英語", "開始": 1, "末尾": 31, "目標周回": 3, "授業進度": 21},
    {"教科": "理科", "開始": 1, "末尾": 34, "目標周回": 3, "授業進度": 28},
    {"教科": "地理", "開始": 1, "末尾": 25, "目標周回": 3, "授業進度": 15},
    {"教科": "歴史", "開始": 1, "末尾": 13, "目標周回": 3, "授業進度": 10},
]

# --- 1. サイドバー：テスト日、ワークの範囲、および「学校の授業進度」の設定 ---
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
st.sidebar.subheader("✏️ 範囲 ＆ 学校の授業進度の設定")
st.sidebar.caption("※「p.1 〜 p.3」のように、ワークの開始ページと終わりのページを設定できます。")

subject_settings = {}
for item in subjects_config:
    subj = item["教科"]
    st.sidebar.markdown(f"--- **{subj}** ---")
    
    col_s, col_e = st.sidebar.columns(2)
    with col_s:
        start_p = st.number_input(f"{subj} 開始P", min_value=1, max_value=300, value=item["開始"], key=f"start_{subj}")
    with col_e:
        end_p = st.number_input(f"{subj} 末尾P (~p)", min_value=1, max_value=300, value=item["末尾"], key=f"end_{subj}")
    
    # いま学校で習っているところ（授業進度ライン：〜p.3 のような指定）
    current_school_p = st.sidebar.number_input(
        f"{subj} の授業進度 (~p)", 
        min_value=start_p, 
        max_value=end_p, 
        value=min(item["授業進度"], end_p),
        key=f"school_{subj}"
    )
    
    target_round = st.sidebar.selectbox(f"{subj} の目標周回", options=[1, 2, 3], index=item["目標周回"]-1, key=f"target_round_{subj}")
    
    subject_settings[subj] = {
        "start": start_p,
        "end": end_p,
        "school_progress": current_school_p,
        "target_round": target_round
    }

# --- 2. メイン画面：ポチポチチェック ＆ ダブル進捗の可視化 ---
st.subheader("🎯 教科別ページチェック（ポチポチ進捗）")
st.caption("タブから教科を選び、終わった「奇数ページ（2ページで1区切り）」にポチポチチェックを入れましょう！")

tabs = st.tabs([item["教科"] for item in subjects_config])
updated_rows = []

for i, tab in enumerate(tabs):
    item = subjects_config[i]
    subj = item["教科"]
    s_p = subject_settings[subj]["start"]
    e_p = subject_settings[subj]["end"]
    school_p = subject_settings[subj]["school_progress"]
    t_round = subject_settings[subj]["target_round"]
    
    # 1周分の奇数ページリストを作成（例: 1, 3, 5, 7, ...）
    odd_pages = list(range(s_p, e_p + 1, 2))
    pages_per_round = len(odd_pages)
    
    with tab:
        st.markdown(f"### 📖 {subj}")
        st.markdown(f"📌 **テスト範囲:** p.{s_p} 〜 ~p.{e_p} ｜ 🏫 **学校の授業進度:** ~p.{school_p} まで ｜ 🎯 **目標:** {t_round}周")
        
        # チェック項目の作成
        all_check_items = []
        for r in range(1, t_round + 1):
            for p in odd_pages:
                all_check_items.append((r, p))
        
        total_items_count = len(all_check_items)
        
        st.write("やったページをポチポチチェック 👇")
        
        checked_count = 0
        for r in range(1, t_round + 1):
            if t_round > 1:
                st.markdown(f"**🔹 【 {r}周目 】**")
            
            cols_grid = st.columns(5)
            for idx, p in enumerate(odd_pages):
                col_target = cols_grid[idx % 5]
                with col_target:
                    chk_key = f"chk_{subj}_r{r}_p{p}"
                    is_checked = st.checkbox(f"p.{p}〜", key=chk_key)
                    if is_checked:
                        checked_count += 1
                        
        # --- 3つの軸の計算 ---
        page_unit = 2
        total_target_pages = total_items_count * page_unit
        done_total_pages = checked_count * page_unit
        remaining_total_pages = max(0, total_target_pages - done_total_pages)
        daily_target = round(remaining_total_pages / remaining_days, 1)
        
        # 授業進度に対する追いつき度
        school_target_pages = max(0, school_p - s_p + 1)
        done_round1_pages = min(pages_per_round * page_unit, done_total_pages)
        catchup_diff = done_round1_pages - school_target_pages
        
        # グラフ用の進捗率
        goal_progress_ratio = checked_count / total_items_count if total_items_count > 0 else 0.0
        
        st.markdown("---")
        
        # 視覚的なダブルプログレスバー
        st.write(f"🏆 **【3周完了ゴールへの進捗】** ({checked_count} / {total_items_count} 区切り完了)")
        st.progress(goal_progress_ratio)
        
        # 授業進度との比較メッセージ
        if catchup_diff >= 0:
            st.success(f"✅ **【授業進度への追いつき】** 習った範囲（~p.{school_p}）に対して、十分完了しています！この調子で2周目・3周目へ進みましょう。")
        else:
            st.warning(f"⚠️ **【授業進度への追いつき】** 現在の授業進度（~p.{school_p}）に対して、あと **{abs(catchup_diff)}ページ分**（1周目の未チェック部分）追いつく必要があります！")
        
        updated_rows.append({
            "教科": subj,
            "範囲": f"p.{s_p} 〜 ~p.{e_p}",
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

# --- 3. 本日のノルマまとめ＆一覧表示 ---
st.subheader("🎯 本日のノルマ・進度サマリー")
st.caption(f"テスト予定日まで あと {remaining_days} 日")

cols = st.columns(len(result_df))
for i, col in enumerate(cols):
    row = result_df.iloc[i]
    left_p = row['残りトータル(P)']
    status = row['追いつき状況']
    
    if left_p > 0:
        delta_text = f"残り {left_p}P (3周)"
    else:
        delta_text = "3周コンプリート！🎉"
        
    col.metric(
        label=row["教科"], 
        value=f"{row['1日ノルマ(P/日)']} ページ/日",
        delta=f"{status} / {delta_text}"
    )

st.subheader("📋 進捗一覧テーブル")
display_df = result_df[["教科", "範囲", "学校進度", "目標", "残りトータル(P)", "1日ノルマ(P/日)", "追いつき状況"]]
st.dataframe(display_df, use_container_width=True)

# 全体の進捗バー
total_target_all = sum([r["_target_total"] for _, r in result_df.iterrows()])
total_done_all = sum([r["_done_total"] for _, r in result_df.iterrows()])
overall_progress = min(1.0, total_done_all / total_target_all) if total_target_all > 0 else 0

st.subheader("🏆 全体目標達成度（3周ベース）")
st.progress(overall_progress, text=f"トータル進捗: {total_done_all} / {total_target_all} ページ完了")
