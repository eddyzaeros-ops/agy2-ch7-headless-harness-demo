#!/usr/bin/env python3
"""
Agy 2.0 Lifecycle Hook 3: PostToolUse (scripts/hooks/post_tool_audit_logger.py)
對應第 7.10.5 節「審計日誌（Audit Logs）」：
每次 Agent 呼叫工具結束後，自動將工具名稱、參數摘要、步驟編號與錯誤狀態寫入 `logs/headless_hook_audit.jsonl`，
並回傳標準 `{}` JSON 物件。
"""

import datetime
import json
import sys
from pathlib import Path

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}

    root_dir = Path(__file__).resolve().parent.parent.parent
    log_dir = root_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    audit_file = log_dir / "headless_hook_audit.jsonl"

    record = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "conversationId": payload.get("conversationId", "headless-ci"),
        "stepIdx": payload.get("stepIdx", 0),
        "toolName": payload.get("toolCall", {}).get("name", "unknown"),
        "toolArgs": payload.get("toolCall", {}).get("args", {}),
        "error": payload.get("error", None),
    }

    with open(audit_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # PostToolUse 契約要求輸出空 JSON 物件 {}
    print("{}")


if __name__ == "__main__":
    main()
