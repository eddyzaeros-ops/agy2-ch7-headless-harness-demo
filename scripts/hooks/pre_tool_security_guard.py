#!/usr/bin/env python3
"""
Agy 2.0 Lifecycle Hook 2: PreToolUse (scripts/hooks/pre_tool_security_guard.py)
在 Agent 執行 run_command / edit_file / write_file 之前進行確定性安全攔截：
- 阻斷任何嘗試存取 `.env`、印出環境變數、或執行 `rm -rf` / `git push --force` 的指令
- 阻斷任何嘗試直接修改生產環境資料庫定義檔 `src/db/schema.sql` 的操作
- 符合安全規範則回傳 `{"decision": "allow"}`
"""

import json
import re
import sys

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


FORBIDDEN_CMD_PATTERNS = [
    (r"rm\s+-rf", "禁止在無頭模式下執行破壞性刪除指令 (rm -rf)"),
    (r"git\s+push\s+.*--force", "禁止在自動化流水線執行強制推送 (git push --force)"),
    (r"\b(printenv|env|set)\b", "違反第 7.10.2 節 Secrets 管理規範：禁止列出環境變數以防憑證洩漏"),
    (r"\.env\b", "禁止直接讀取或修改 .env 敏感配置檔"),
]

PROTECTED_FILES = {"src/db/schema.sql", ".env"}


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        print(json.dumps({"decision": "allow"}))
        return

    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})

    if tool_name == "run_command":
        cmd = str(args.get("CommandLine", ""))
        for pat, reason in FORBIDDEN_CMD_PATTERNS:
            if re.search(pat, cmd, re.IGNORECASE):
                print(json.dumps({"decision": "deny", "reason": f"[PreToolUse Security Gate] {reason}"}))
                return

    elif tool_name in ("edit_file", "write_file"):
        target_path = str(args.get("Path", "")).replace("\\", "/")
        for pf in PROTECTED_FILES:
            if target_path.endswith(pf):
                print(
                    json.dumps({
                        "decision": "deny",
                        "reason": f"[PreToolUse Security Gate] 受保護檔案 `{pf}` 禁止由 Agent 修改！",
                    })
                )
                return

    print(json.dumps({"decision": "allow", "reason": "Passed PreToolUse deterministic security check."}))


if __name__ == "__main__":
    main()
