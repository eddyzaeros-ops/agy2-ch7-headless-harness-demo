#!/usr/bin/env python3
"""
Agy 2.0 Lifecycle Hook 1: SessionStart (scripts/hooks/on_session_start.py)
當 Headless Agent 會話啟動時自動執行，從 stdin 讀取會話 Metadata，
並透過 stdout 回傳 injectSteps，將當前環境狀態與強制審查提醒注入對話。
"""

import json
import sys

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}

    conv_id = payload.get("conversationId", "headless-session")
    model_name = payload.get("modelName", "auto")

    output = {
        "injectSteps": [
            {
                "systemMessage": {
                    "systemMessage": (
                        f"[Hook:SessionStart] 已啟動 Agy 2.0 Headless 受控環境 (session={conv_id}, model={model_name})。"
                        "提醒：1. 必須啟用 `payment-security-audit` 技能 "
                        "2. 必須呼叫 `sqlite-schema-mcp` 核對資料庫真實欄位 "
                        "3. 嚴禁修改 `.env` 或 `src/db/schema.sql`。"
                    )
                }
            }
        ]
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
