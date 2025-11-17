import os
import sys
import datetime
from typing import List, Dict, Any

import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# 加载 .env（优先当前工作目录；若提供 ENV_PATH 则覆盖）
load_dotenv()
custom_env = os.environ.get("ENV_PATH")
if custom_env:
    load_dotenv(dotenv_path=custom_env, override=True)

DB_CONFIG = {
    "host": os.getenv("postgre_host"),
    "port": int(os.getenv("postgre_port", 5432)),
    "database": os.getenv("postgre_db"),
    "user": os.getenv("postgre_user"),
    "password": os.getenv("postgre_password"),
}

st.set_page_config(page_title="Fixtures Dashboard", page_icon="⚽", layout="wide")
st.title("⚽ 比赛选择与报告生成")
st.caption("从 PostgreSQL 读取 fixtures，选择比赛并生成基本面报告")

@st.cache_data(ttl=60)
def fetch_fixtures() -> pd.DataFrame:
    """从数据库读取指定字段，并对 fixture_date 做 +8h 展示处理。"""
    # 基本校验，避免 host 缺失导致走本地socket
    if not DB_CONFIG.get("host"):
        raise RuntimeError("未配置 postgre_host，请在 .env 或环境变量中设置数据库主机地址")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        raise RuntimeError(f"数据库连接失败: {e}")

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute(
                    """
                    SELECT fixture_id, fixture_date, league_name,
                           teams_home_name, teams_away_name
                    FROM fixtures
                    WHERE ((fixture_date + INTERVAL '8 hour')::date) IN (CURRENT_DATE, CURRENT_DATE + INTERVAL '1 day')
                    ORDER BY fixture_date DESC
                    """
                )
            except Exception:
                # 兼容旧库：无法对fixture_date加interval时回退到全量查询
                cur.execute(
                    """
                    SELECT fixture_id, fixture_date, league_name,
                           teams_home_name, teams_away_name
                    FROM fixtures
                    ORDER BY fixture_date DESC
                    """
                )
            rows: List[Dict[str, Any]] = cur.fetchall()
    except Exception as e:
        raise RuntimeError(f"查询失败: {e}")
    finally:
        conn.close()

    # 处理 fixture_date +8h
    processed = []
    for r in rows:
        dt = r.get("fixture_date")
        if isinstance(dt, datetime.datetime):
            dt_plus_8 = dt + datetime.timedelta(hours=8)
        else:
            # 尝试字符串解析
            try:
                dt_obj = datetime.datetime.fromisoformat(str(dt))
                dt_plus_8 = dt_obj + datetime.timedelta(hours=8)
            except Exception:
                dt_plus_8 = None
        processed.append(
            {
                "fixture_id": r.get("fixture_id"),
                "fixture_date(+8h)": dt_plus_8.strftime("%Y-%m-%d %H:%M") if dt_plus_8 else "",
                "league_name": r.get("league_name"),
                "teams_home_name": r.get("teams_home_name"),
                "teams_away_name": r.get("teams_away_name"),
            }
        )

    df = pd.DataFrame(processed)
    # 添加选择列，默认 False
    if len(df) > 0:
        df.insert(0, "选择", False)
    
    # 仅保留今明两天（按 +8h 后的本地日期）
    try:
        today_local = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).date()
        tomorrow_local = today_local + datetime.timedelta(days=1)
        df = df[df["fixture_date(+8h)"].apply(
            lambda s: (pd.to_datetime(s).date() if isinstance(s, str) and s else None) in {today_local, tomorrow_local}
        )]
    except Exception:
        pass

    return df

# 数据加载与展示
try:
    df = fetch_fixtures()
except Exception as e:
    st.error(str(e))
    st.stop()

st.subheader("比赛列表")
st.write("在下方表格中勾选要生成报告的比赛（仅支持单选）")

edited_df = st.data_editor(
    df,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    column_config={
        "选择": st.column_config.CheckboxColumn(required=False),
        "fixture_id": st.column_config.NumberColumn(format="%d"),
        "fixture_date(+8h)": st.column_config.TextColumn(),
        "league_name": st.column_config.TextColumn(),
        "teams_home_name": st.column_config.TextColumn(),
        "teams_away_name": st.column_config.TextColumn(),
    },
    disabled=["fixture_id", "fixture_date(+8h)", "league_name", "teams_home_name", "teams_away_name"],
    key="fixtures_table",
)

selected_rows = edited_df[edited_df["选择"] == True]

col_left, col_right = st.columns([1, 3])
with col_left:
    generate = st.button("生成报告", type="primary")
with col_right:
    if selected_rows.shape[0] == 0:
        st.info("请勾选一场比赛再点击『生成报告』。")
    elif selected_rows.shape[0] > 1:
        st.warning("目前只支持单选，请仅勾选一场比赛。")

if generate:
    if selected_rows.shape[0] != 1:
        st.error("请选择且仅选择一场比赛！")
        st.stop()

    fixture_id = int(selected_rows.iloc[0]["fixture_id"])  # 保证为 int
    st.write(f"已选择比赛 fixture_id: {fixture_id}")

    # 导入并调用报告生成
    with st.spinner("正在生成基本面报告，请稍候..."):
        try:
            # 确保可以导入同目录模块
            sys.path.append("/Users/kuriball/Documents/MyProjects/agent/bc_agent")
            from match_fundamentals_analyst import test_fundamentals_analyst

            result = test_fundamentals_analyst(fixture_id=int(fixture_id))
            report = result.get("fundamentals_repost")

            if not report:
                # 回退到最后一条消息内容（如果存在）
                msgs = result.get("messages")
                if isinstance(msgs, list) and len(msgs) > 0 and hasattr(msgs[-1], "content"):
                    report = msgs[-1].content
        except Exception as e:
            st.error(f"生成报告失败: {e}")
            st.stop()

    if report:
        st.success("报告生成成功！")
        st.markdown(report)
    else:
        st.warning("未生成报告内容，请检查工具调用或API配置。")