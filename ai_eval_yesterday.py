from __future__ import annotations

import os
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import logging
import sys
import time

from dotenv import load_dotenv
import psycopg2

load_dotenv()
from psycopg2.extras import RealDictCursor

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from langchain_core.messages import HumanMessage

# 复用现有分析图
from match_fundamentals_analyst import graph


load_dotenv()

LOG_LEVEL = os.getenv("AI_EVAL_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("ai_eval")

def _ensure_v1_base_url(url: str | None) -> str | None:
    """确保 base_url 以 /v1 结尾，兼容 OpenAI 风格后端。"""
    if not url:
        return url
    u = url.rstrip("/")
    if not u.endswith("/v1"):
        u = f"{u}/v1"
    return u


def get_db_conn():
    logger.info(
        "Connecting to PostgreSQL host=%s port=%s db=%s user=%s",
        os.getenv("postgre_host"),
        os.getenv("postgre_port", "5432"),
        os.getenv("postgre_db"),
        os.getenv("postgre_user"),
    )
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        connect_timeout=int(os.getenv("POSTGRE_CONNECT_TIMEOUT", "10")),
        application_name="ai_eval",
        keepalives=1,
        keepalives_idle=int(os.getenv("POSTGRE_KEEPALIVES_IDLE", "30")),
        keepalives_interval=int(os.getenv("POSTGRE_KEEPALIVES_INTERVAL", "10")),
        keepalives_count=int(os.getenv("POSTGRE_KEEPALIVES_COUNT", "5")),
    )
    _configure_session(conn)
    return conn


def _configure_session(conn) -> None:
    """配置连接会话级参数以减少长时间阻塞与空闲超时。"""
    try:
        with conn.cursor() as cur:
            # 限制单条语句最长执行时间 30s；避免事务长时间空闲 30s
            cur.execute("SET statement_timeout TO 30000;")
            cur.execute("SET idle_in_transaction_session_timeout TO 30000;")
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        # 非关键配置失败不影响主流程
        logger.debug("Session config skipped due to error", exc_info=True)


def parse_league_ids() -> List[int]:
    raw = os.getenv("LEAGUE_IDS", "")
    ids: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            continue
    return ids


def ensure_ai_eval_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_eval (
                fixture_id INTEGER PRIMARY KEY,
                report_md TEXT NOT NULL,
                if_bet INTEGER NOT NULL,
                predict_winner INTEGER NOT NULL,
                confidence DOUBLE PRECISION NOT NULL,
                key_tag_evidence TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
            );
            """
        )
        # 保障旧表结构也具备该列
        cur.execute("ALTER TABLE ai_eval ADD COLUMN IF NOT EXISTS key_tag_evidence TEXT;")
    conn.commit()
    logger.info("Ensured ai_eval table exists")


def fetch_recent_fixture_ids(conn) -> List[int]:
    leagues = parse_league_ids()
    if not leagues:
        logger.warning("No league ids parsed from LEAGUE_IDS env; skipping fetch")
        return []

    # 计算 UTC 今天和明天的时间范围
    now_utc = datetime.now(timezone.utc)
    today_date = now_utc.date()
    start_utc = datetime(today_date.year, today_date.month, today_date.day, 0, 0, 0, tzinfo=timezone.utc)
    end_utc = start_utc + timedelta(days=2)

    logger.info(
        "Fetching fixtures for UTC range [%s, %s) leagues=%s",
        start_utc.isoformat(),
        end_utc.isoformat(),
        leagues,
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT fixture_id
            FROM api_football_fixtures
            WHERE league_id = ANY(%s)
              AND fixture_date >= %s
              AND fixture_date < %s
            ORDER BY fixture_id ASC
            """,
            (leagues, start_utc, end_utc),
        )
        all_fixture_ids = [r[0] for r in cur.fetchall()]
        if not all_fixture_ids:
            logger.info("No fixtures found in the given time range.")
            return []

        # 查询 ai_eval 表中已经存在的 fixture_id
        cur.execute(
            """
            SELECT fixture_id
            FROM ai_eval
            WHERE fixture_id = ANY(%s)
            """,
            (all_fixture_ids,),
        )
        existing_fixture_ids = {r[0] for r in cur.fetchall()}
        logger.info("Found %d existing fixtures in ai_eval table.", len(existing_fixture_ids))

    # 过滤掉已经存在的 fixture_id
    fixture_ids_to_process = [fid for fid in all_fixture_ids if fid not in existing_fixture_ids]

    logger.info("Found %d fixtures for today and tomorrow", len(fixture_ids_to_process))
    return fixture_ids_to_process


def generate_markdown_report(fixture_id: int) -> str:
    logger.info("Generating fundamentals report for fixture_id=%s", fixture_id)
    t0 = time.perf_counter()
    initial_state = {
        "messages": [HumanMessage(content=f"Analyze the fundamentals data for fixture with id {fixture_id}")],
        "fixture_id": fixture_id,
        "sender": "user",
        "fundamentals_report": "",
    }
    result = graph.invoke(initial_state)

    md = result.get("fundamentals_repost") or ""
    if not md:
        msgs = result.get("messages") or []
        if msgs:
            last_msg = msgs[-1]
            md = getattr(last_msg, "content", "") or ""
    dt = time.perf_counter() - t0
    logger.info("Report generated for fixture_id=%s, chars=%d, time=%.2fs", fixture_id, len(md), dt)
    if not md:
        logger.warning("Empty report for fixture_id=%s", fixture_id)
    return md


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("YUNWU_MODEL") or "gpt-5",
        api_key=os.getenv("YUNWU_API_KEY"),
        base_url=_ensure_v1_base_url(os.getenv("YUNWU_API_BASE_URL")),
    )


def summarize_and_decide(md_report: str, fixture_id: int) -> Dict[str, Any]:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a highly constrained football betting analyst. Your sole task is to analyze the provided Markdown fundamentals report and output the prediction data. STRICTLY adhere to the following rules:"
                " 1. Output MUST be a single-line, valid JSON object."
                " 2. DO NOT include any markdown, code fences (```json), explanations, or preamble."
                " 3. Use the exact following structure (Schema Definition):"
                "    - 'if_bet': Integer (1 = Yes, 0 = No)"
                "    - 'predict_winner': Integer (3 = Home Win, 1 = Draw, 0 = Away Win)"
                "    - 'confidence': Float (ranging from 0.0 to 1.0)"
                "    - 'key_tag_evidence': String (Core evidence tags, separated by a '/' character, e.g., 'Team A has strong motivation/Team B has injured players/Team A has poor defense')."
                " Example output format: "
            ),
            (
                "human",
                "Fixture {fixture_id} report:\n\n{report}",
            ),
        ]
    )

    def _parse_json_line(text: str) -> Dict[str, Any]:
        stripped = text.strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            start = stripped.find("{")
            end = stripped.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(stripped[start : end + 1])
            raise

    llm = get_llm()
    chain = prompt | llm
    try:
        response = chain.invoke({"fixture_id": fixture_id, "report": md_report})
        content = getattr(response, "content", str(response))
        raw_decision = _parse_json_line(content)
    except Exception as e:
        logger.warning(
            "Failed to summarize report for fixture_id=%s: %s", fixture_id, e
        )
        return {"if_bet": 0, "predict_winner": 1, "confidence": 0.0, "key_tag_evidence": ""}

    decision = {
        "if_bet": int(raw_decision.get("if_bet", 0)),
        "predict_winner": int(raw_decision.get("predict_winner", 1)),
        "confidence": float(raw_decision.get("confidence", 0.0)),
        "key_tag_evidence": str(raw_decision.get("key_tag_evidence", "")),
    }
    decision["confidence"] = max(0.0, min(1.0, decision["confidence"]))
    logger.info(
        "LLM decision for fixture_id=%s -> if_bet=%s predict_winner=%s confidence=%.3f tags=%s",
        fixture_id,
        decision["if_bet"],
        decision["predict_winner"],
        decision["confidence"],
        decision["key_tag_evidence"],
    )
    return decision


def upsert_ai_eval(conn, fixture_id: int, md_report: str, decision: Dict[str, Any]) -> None:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ai_eval (fixture_id, report_md, if_bet, predict_winner, confidence, key_tag_evidence, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC')
                ON CONFLICT (fixture_id) DO UPDATE SET
                    report_md = EXCLUDED.report_md,
                    if_bet = EXCLUDED.if_bet,
                    predict_winner = EXCLUDED.predict_winner,
                    confidence = EXCLUDED.confidence,
                    key_tag_evidence = EXCLUDED.key_tag_evidence,
                    updated_at = NOW() AT TIME ZONE 'UTC'
                ;
                """,
                (
                    fixture_id,
                    md_report,
                    int(decision["if_bet"]),
                    int(decision["predict_winner"]),
                    float(decision["confidence"]),
                    str(decision.get("key_tag_evidence", "")),
                ),
            )
        conn.commit()
        logger.info("Upserted ai_eval row for fixture_id=%s", fixture_id)
    except psycopg2.OperationalError as e:
        # 尝试回滚以恢复连接状态
        try:
            conn.rollback()
        except Exception:
            pass
        raise


def run_ai_eval() -> List[Dict[str, Any]]:
    logger.info("Starting AI evaluation run")
    conn = get_db_conn()
    try:
        ensure_ai_eval_table(conn)
        fixture_ids = fetch_recent_fixture_ids(conn)
        logger.info("Processing %d fixtures", len(fixture_ids))

        results: List[Dict[str, Any]] = []
        total = len(fixture_ids)
        for idx, fid in enumerate(fixture_ids, start=1):
            logger.info("[%d/%d] Fixture %s", idx, total, fid)
            try:
                md = generate_markdown_report(fid)
                if not md:
                    decision = {"if_bet": 0, "predict_winner": 1, "confidence": 0.0}
                else:
                    decision = summarize_and_decide(md, fid)

                # 首次写入尝试
                try:
                    upsert_ai_eval(conn, fid, md, decision)
                except psycopg2.OperationalError:
                    logger.warning("DB timeout on upsert fixture_id=%s, reconnecting and retrying once", fid)
                    try:
                        conn.close()
                    except Exception:
                        pass
                    conn = get_db_conn()
                    ensure_ai_eval_table(conn)
                    time.sleep(0.5)
                    upsert_ai_eval(conn, fid, md, decision)
                results.append({"fixture_id": fid, **decision})
            except Exception as e:
                logger.exception("Error processing fixture_id=%s: %s", fid, e)

        return results
    finally:
        conn.close()
        logger.info("AI evaluation run finished")


if __name__ == "__main__":
    output = run_ai_eval()
    print(json.dumps(output, ensure_ascii=False))
