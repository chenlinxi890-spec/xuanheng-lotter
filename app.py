import json
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from xuanheng.games import GAMES, validate_record, template_columns
from xuanheng.storage import init_db, upsert_records, load_records, count_records
from xuanheng.ingest import parse_csv, export_records
from xuanheng.analysis import analyze_game, build_candidate, bias_report

st.set_page_config(page_title="玄衡 · 易数数字彩", page_icon="☯", layout="wide")
init_db()

st.title("☯ 玄衡 · 易数数字彩分析系统")
st.caption("历史数据整理 · 位置统计 · 透明候选生成")

with st.sidebar:
    st.subheader("玩法")
    game = st.selectbox("选择玩法", list(GAMES), format_func=lambda k: GAMES[k]["name"])
    st.divider()
    st.caption("本地运行 · SQLite 数据库")
    st.caption("统计结果不代表未来开奖概率。")

tabs = st.tabs(["走势分析", "号码筛选", "数据管理", "易数笔记", "项目说明", "偏差检测"])

with tabs[0]:
    records = load_records(game)
    st.subheader(f"{GAMES[game]['name']} · 数据概览")
    a, b, c = st.columns(3)
    a.metric("已存期数", len(records))
    b.metric("最新期号", records[0]["issue"] if records else "暂无")
    c.metric("玩法", GAMES[game]["name"])
    if not records:
        st.info("当前没有历史数据。请先到“数据管理”导入 CSV。")
    else:
        window = st.slider("近期统计窗口", 20, min(500, max(20, len(records))), min(100, max(20, len(records))), 10)
        result = analyze_game(game, records, window)
        st.markdown("#### 位置数字频率")
        freq = result["position_frequency"]
        for pos, counts in freq.items():
            df = pd.DataFrame({"数字": list(counts.keys()), "出现次数": list(counts.values())})
            st.write(pos)
            st.plotly_chart(px.bar(df, x="数字", y="出现次数", text="出现次数"), use_container_width=True)
        st.markdown("#### 近期结构")
        st.json(result["structure"])
        st.markdown("#### 最近开奖")
        st.dataframe(pd.DataFrame(records[:20]), use_container_width=True, hide_index=True)

with tabs[1]:
    records = load_records(game)
    st.subheader("按近期统计生成候选")
    st.caption("候选按各位置近期频数排序直接生成，不依赖人工指定范围。")
    window = st.slider("参考近期窗口", 20, 500, 100, 10, key="candidate_window")
    if st.button("生成一组参考候选", type="primary", disabled=not records):
        candidate = build_candidate(game, records, window)
        if candidate.get("error"):
            st.error(candidate["error"])
        else:
            st.success("候选已生成（启发式参考，不是中奖概率）")
            st.subheader(candidate["display"])
            st.write(candidate["explanation"])
            st.json(candidate["metrics"])
            st.download_button("下载候选 JSON", json.dumps(candidate, ensure_ascii=False, indent=2), file_name=f"{game}_candidate.json")
    if not records:
        st.info("请先导入历史数据。")

with tabs[2]:
    st.subheader("数据管理")
    st.write("下载模板，填入真实开奖数据，再上传 CSV。")
    template = template_columns(game)
    st.download_button("下载当前玩法 CSV 模板", template.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"{game}_template.csv", mime="text/csv")
    uploaded = st.file_uploader("上传历史开奖 CSV", type=["csv"], key=f"upload_{game}")
    if uploaded is not None:
        try:
            parsed = parse_csv(game, uploaded.getvalue())
            st.write(f"解析到 {len(parsed)} 条记录")
            st.dataframe(pd.DataFrame(parsed[:10]), use_container_width=True)
            if st.button("确认导入数据库", type="primary"):
                upsert_records(game, parsed)
                st.success(f"已导入/更新 {len(parsed)} 条记录。")
                st.rerun()
        except Exception as e:
            st.error(f"导入失败：{e}")
    records = load_records(game)
    if records:
        st.download_button("导出当前玩法全部数据", export_records(game, records),
                           file_name=f"{game}_history.csv", mime="text/csv")
        if st.button("清空当前玩法数据", type="secondary"):
            from xuanheng.storage import clear_game
            clear_game(game)
            st.warning("当前玩法数据已清空。")
            st.rerun()

with tabs[3]:
    st.subheader("易数观察笔记")
    st.warning("本模块是传统数理观察记录，不是可验证的开奖预测模型。不得将象数解释当作统计证据。")
    note = st.text_area("记录本期观察（例如数理取象、五行映射、推演过程）", height=160,
                        placeholder="记录依据、日期、玩法与观察结论……")
    if st.button("导出本条笔记") and note.strip():
        st.download_button("下载笔记", note.encode("utf-8"), file_name="xuanheng_yishu_note.txt")

with tabs[4]:
    st.subheader("项目范围")
    st.markdown("""
    - 支持排列三、排列五、大乐透、双色球、七星彩。
    - 数据由用户导入，保存在本地 SQLite。
    - 统计包括位置频率、近期频率、遗漏、和值/跨度及形态。
    - 候选按可解释的启发式评分排序；不输出虚构命中率。
    - 排列三与排列五联动时，排五前三位严格沿用排三候选。
    """)
    st.caption("请理性参与彩票活动。任何历史统计都不能消除随机性。")

with tabs[5]:
    records = load_records(game)
    st.subheader("偏差检测")
    st.caption("检验这段样本是否与均匀随机一致。显著偏离只说明这段样本里不均匀，不等于能预测下一期；不显著也不证明绝对均匀。")
    window = st.slider("检测窗口（期数）", 20, 500, 500, 10, key="bias_window")
    if st.button("开始检测", type="primary", disabled=not records):
        report = bias_report(game, records, window)
        if report.get("error"):
            st.error(report["error"])
        else:
            st.write(f"检测窗口：最近 {report['window']} 期")
            table = pd.DataFrame([{
                "位置": p["label"],
                "样本量": p["n"],
                "期望频数": p["expected"],
                "卡方值": p["chi2"],
                "卡方 p 值": p["chi2_p"],
                "游程 Z": p["runs_z"],
                "游程 p 值": p["runs_p"],
                "结论": p["conclusion"] + ("（" + p["runs_flag"] + "）" if p["runs_flag"] else ""),
            } for p in report["positions"]])
            st.dataframe(table, use_container_width=True, hide_index=True)
            for note in report["notes"]:
                st.caption(note)
            st.download_button("下载检测报告 JSON", json.dumps(report, ensure_ascii=False, indent=2), file_name=f"{game}_bias_report.json")
    if not records:
        st.info("请先导入历史数据。")
