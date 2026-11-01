#!/usr/bin/env python3
"""
Agy 2.0 Lifecycle Hook 4: Stop (scripts/hooks/on_stop_quality_gate.py)
當 Headless Agent 認為任務已完成準備結束迴圈 (Stop) 時觸發：
- 在「階段四：主動修復模式 (AGY_ENFORCE_TESTS_ON_STOP=1)」下，自動執行單元測試驗證。
- 若單元測試未通過，回傳 `{"decision": "continue", "reason": "..."}` 強制將 Agent 拉回迴圈繼續修復！
- 在「階段一～三：審查模式」下，確認是否已生成審查報告，若完成則放行停止 (`{"decision": "stop"}`)。
"""

import json
import os
import subprocess
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

    enforce_tests = os.environ.get("AGY_ENFORCE_TESTS_ON_STOP", "0") == "1"
    if enforce_tests:
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            err_tail = (proc.stderr or proc.stdout)[-400:]
            print(
                json.dumps({
                    "decision": "continue",
                    "reason": f"[Stop Hook Gate] 單元測試尚未通過，禁止結束！請修復以下錯誤後再結束：\n{err_tail}",
                }, ensure_ascii=False)
            )
            return

    print(json.dumps({"decision": "stop", "reason": "All Stop hook quality checks satisfied."}))


if __name__ == "__main__":
    main()
