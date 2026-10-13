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

st.title("📚 定期テスト 計画＆進捗管理アプリ（中間・期末対応）")
st.write("✨ 中間テスト・期末テストの2段階で、それぞれの期限・範囲・目標を個別に管理できます！")

# 初期データの設定（教科ごとのデフォルト値）
subjects_config = [
    {"教科": "国語", "中間末尾": 20, "期末末尾": 39, "目標周回": 3, "授業進度": 15},
    {"教科": "数学", "中間末尾": 18, "期末末尾": 37, "目標周回": 3, "授業進度": 16},
    {"教科": "英語", "中間末尾": 15, "期末末尾": 31, "目標周回": 3, "授業進度": 12},
    {"教科": "理科", "中間末尾": 17, "期末末尾": 34, "目標周回": 3, "授業進度": 14},
    {"教科": "地理", "中間末尾": 12, "期末末尾": 25, "目標周回": 3, "授業進度": 10},
    {"教科": "歴史", "中間末尾": 6, "期末末尾": 13, "目標周回": 3, "授業進度": 5},
]

# --- 1. サイドバー：テスト段階の切り替え ＆ 日付・範囲設定 ---
st.sidebar.header("🗓️ テスト段階・期限の設定")

# どのテストを管理するかを選択
test_stage = st.sidebar.radio("管理するテストを選択", options=["中間テスト", "期末テスト"], index=0)

target_date = st.sidebar.date_input(f"{test_stage} 予定日", date.today())
today = date.today()
remaining_days = (target_date - today).days

if remaining_days <= 0:
    remaining_days = 1
    st.sidebar.warning("⚠️ 予定日が本日以前になっています。")
else:
    st.sidebar.info(f"⏳ {test_stage} まで **あと {remaining_days} 日** です！")

st.sidebar.divider()
st.sidebar.subheader(f"✏️ {test_stage} の範囲 ＆ 進度設定")
st.sidebar.caption("※中間・期末それぞれの範囲や授業進度を設定できます。")

subject_settings = {}
for item in subjects_config:
    subj = item["教科"]
    st.sidebar.markdown(f"--- **{subj}** ---")
    
    # テスト段階に応じてデフォルトの範囲を切り替え
    if test_stage == "中間テスト":
        default_end = item["中间末尾" if "中间末尾" in item else "中間末尾"]
        start_p = 2
        end_p = st.sidebar.number_input(f"{subj} 中間末尾P", min_value=1, max_value=300, value=default_end, key=f"mid_end_{subj}")
    else:
        # 期末の場合、中間の終わりから期末の終わりまで、あるいは最初から期末まで
        start_p = 2
        end_p = st.sidebar.number_input(f"{subj} 期末末尾P", min_value=1, max_value=300, value=item["期末末尾"], key=f"fin_end_{subj}")
    
    # いま学校で習っているところ
    current_school_p = st.sidebar.number_input(
        f"{subj} の授業進度 (~p)", 
        min_value=start_p, 
        max_value=end_p, 
        value=min(item["授業進度"], end_p),
        key=f"school_{test_stage}_{subj}"
    )
    
    target_round = st.sidebar.selectbox(f"{subj} の目標周回", options=[1, 2, 3], index=item["目標周回"]-1, key=f"round_{test_stage}_{subj}")
    
    subject_settings[subj] = {
        "start": start_p,
        "end": end_p,
        "school_progress": current_school_p,
        "target_round": target_round
    }

# --- 2. メイン画面：ポチポチチェック ＆ ダブル進捗の可視化 ---
st.subheader(f"🎯 教科別ページチェック（{test_stage}対策）")
st.caption(f"タブから教科を選び、{test_stage}範囲の終わった区切り（〜p.3、〜p.5…）にポチポチチェックを入れましょう！")

tabs = st.tabs([item["教科"] for item in subjects_config])
updated_rows = []

for i, tab in enumerate(tabs):
    item = subjects_config[i]
    subj = item["教科"]
    s_p = subject_settings[subj]["start"]
    e_p = subject_settings[subj]["end"]
    school_p = subject_settings[subj]["school_progress"]
    t_round = subject_settings[subj]["target_round"]
    
    # 2ページ単位（見開き）のブロックを生成
    page_blocks = []
    current = s_p
    while current <= e_p:
        next_p = min(current + 1, e_p)
        page_blocks.append((current, next_p))
        current += 2
        
    pages_per_round = len(page_blocks)
    
    with tab:
        st.markdown(f"### 📖 {subj} （{test_stage}）")
        st.markdown(f"📌 **範囲:** p.{s_p} 〜 p.{e_p} ｜ 🏫 **学校の授業進度:** ~p.{school_p} まで ｜ 🎯 **目標:** {t_round}周")
        
        total_items_count = pages_per_round * t_round
        st.write("やったページをポチポチチェック 👇")
        
        checked_count = 0
        for r in range(1, t_round + 1):
            if t_round > 1:
                st.markdown(f"**🔹 【 {r}周目 】**")
            
            cols_grid = st.columns(5)
            for idx, (p_start, p_end) in enumerate(page_blocks):
                col_target = cols_grid[idx % 5]
                with col_target:
                    # キーにテスト段階を含めることで、中間と期末でチェック状態を独立して保持できます
                    chk_key = f"chk_{test_stage}_{subj}_r{r}_p{p_start}"
                    label_text = f"〜p.{p_end}"
                    is_checked = st.checkbox(label_text, key=chk_key)
                    if is_checked:
                        checked_count += 1
                        
        # --- 計算処理 ---
        page_unit = 2
        total_target_pages = total_items_count * page_unit
        done_total_pages = checked_count * page_unit
        remaining_total_pages = max(0, total_target_pages - done_total_pages)
        daily_target = round(remaining_total_pages / remaining_days, 1)
        
        # 授業進度に対する追いつき度
        school_target_pages = max(0, school_p - s_p + 1)
        done_round1_pages = min(pages_per_round * page_unit, done_total_pages)
        catchup_diff = done_round1_pages - school_target_pages
        
        goal_progress_ratio = checked_count / total_items_count if total_items_count > 0 else 0.0
        
        st.markdown("---")
        
        st.write(f"🏆 **【{test_stage} 目標ゴールへの進捗】** ({checked_count} / {total_items_count} 区切り完了)")
        st.progress(goal_progress_ratio)
        
        if catchup_diff >= 0:
            st.success(f"✅ **【授業進度への追いつき】** 習った範囲（~p.{school_p}）に対して、十分完了しています！この調子で2周目・3周目へ進みましょう。")
        else:
            st.warning(f"⚠️ **【授業進度への追いつき】** 現在の授業進度（~p.{school_p}）に対して、あと **{abs(catchup_diff)}ページ分**（1周目の未チェック部分）追いつく必要があります！")
        
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

# --- 3. 本日のノルマまとめ＆一覧表示 ---
st.subheader(f"🎯 本日のノルマ・進度サマリー（{test_stage}）")
st.caption(f"{test_stage} 予定日まで あと {remaining_days} 日")

cols = st.columns(len(result_df))
for i, col in enumerate(cols):
    row = result_df.iloc[i]
    left_p = row['残りトータル(P)']
    status = row['追いつき状況']
    
    if left_p > 0:
        delta_text = f"残り {left_p}P ({row['目標']})"
    else:
        delta_text = "目標コンプリート！🎉"
        
    col.metric(
        label=row["教科"], 
        value=f"{row['1日ノルマ(P/日)']} ページ/日",
        delta=f"{status} / {delta_text}"
    )

st.subheader("📋 進捗一覧テーブル")
display_df = result_df[["教科", "範囲", "学校進度", "目標", "残りトータル(P)", "1日ノルマ(P/日)", "追いつき状況"]]
st.dataframe(display_df, use_container_width=True)

total_target_all = sum([r["_target_total"] for _, r in result_df.iterrows()])
total_done_all = sum([r["_done_total"] for _, r in result_df.iterrows()])
overall_progress = min(1.0, total_done_all / total_target_all) if total_target_all > 0 else 0

st.subheader(f"🏆 全体目標達成度（{test_stage}ベース）")
st.progress(overall_progress, text=f"トータル進捗: {total_done_all} / {total_target_all} ページ完了")
