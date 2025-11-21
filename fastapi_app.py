from fastapi import FastAPI, Query, Response, HTTPException
from fastapi.responses import PlainTextResponse
from langchain_core.messages import HumanMessage

# 直接复用现有的分析图逻辑
from match_fundamentals_analyst import graph

app = FastAPI(title="Fundamentals Analyst API", version="0.1.0")


@app.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    return "ok"


@app.get("/fundamentals", summary="生成比赛基本面Markdown报告", response_class=PlainTextResponse)
async def get_fundamentals(
    fixture_id: int = Query(..., description="比赛 fixture_id，整数")
):
    """
    传入 fixture_id，调用现有 LangGraph，返回 Markdown 字符串。

    注意：match_fundamentals_analyst 内部使用环境变量配置 LLM：
    - `YUNWU_MODEL`（可选，默认 `gpt-4o-mini`）
    - `YUNWU_API_KEY`（必填，否则会报鉴权错误）
    - `YUNWU_API_BASE_URL`（可选，自动补全为 /v1）
    """
    try:
        initial_state = {
            "messages": [HumanMessage(content=f"分析比赛id为 {fixture_id} 的基本面数据")],
            "fixture_id": fixture_id,
            "sender": "user",
            # 保持与原测试一致，图最终返回 "fundamentals_repost"
            "fundamentals_report": "",
        }

        result = graph.invoke(initial_state)

        # 结果优先从自定义键中取 Markdown
        md = result.get("fundamentals_repost") or ""

        # 如果为空，尝试从最后一条消息兜底（尽管图在结束时会清理消息）
        if not md:
            msgs = result.get("messages") or []
            if msgs:
                last_msg = msgs[-1]
                md = getattr(last_msg, "content", "") or ""

        if not md:
            # 明确提示生成失败，便于前端或调用方处理
            raise HTTPException(status_code=502, detail="未能生成报告（内容为空）。")

        # 以 Markdown 文本返回
        return Response(content=md, media_type="text/markdown; charset=utf-8")

    except HTTPException:
        raise
    except Exception as e:
        # 捕获所有异常，避免泄露栈信息
        raise HTTPException(status_code=500, detail=f"生成报告失败：{type(e).__name__}: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "fastapi_app:app", host="0.0.0.0", port=8000, reload=False
    )