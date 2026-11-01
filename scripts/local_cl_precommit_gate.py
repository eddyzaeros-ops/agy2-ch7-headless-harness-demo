#!/usr/bin/env python3
"""
本地 CL 提交前自檢門禁 (scripts/local_cl_precommit_gate.py & .githooks/pre-commit)
當開發者在本地執行 `git commit` 時自動觸發：
1. 呼叫 PreToolUse Hook 確保環境安全
2. 呼叫 `payment-security-audit` Skill 的 `ast_pci_scanner.py` 與 `sqlite-schema-mcp`
3. 若發現 Critical 級別問題，立即印出修復建議並回傳 Exit Code 1 攔截本地 Commit！
"""

import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    root_dir = Path(__file__).resolve().parent.parent
    print("🔍 [Local CL Pre-Commit Gate] 正在執行 Agy 2.0 Headless 6-Harness 本地提交前自檢...")

    proc = subprocess.run(
        [sys.executable, str(root_dir / "scripts" / "agy_sdk_headless_runner.py"), "--gate-mode", "observer"],
        capture_output=True,
        text=True,
        cwd=str(root_dir),
    )
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        sys.exit(proc.returncode)

    data = json.loads(proc.stdout)
    structured = data["structured_output"]
    verdict = structured["verdict"]
    crit = structured["critical_count"]

    print(f"📊 審查判定: {verdict} (Critical: {crit}, Warning/Suggestion: {structured['warning_count']})")
    for idx, issue in enumerate(structured["issues"], start=1):
        print(f"  {idx}. [{issue['severity'].upper()}] {issue['file']}:{issue['line']} ({issue['rule_id']}) - {issue['problem']}")
        print(f"     💡 修復建議: {issue['fix']}")

    if crit > 0:
        print("\n❌ [Pre-Commit Gate] 偵測到 Critical 級別資安或 Schema 問題，建議修復後再提交！")
        sys.exit(1)

    print("\n✅ [Pre-Commit Gate] 本地 CL 檢查通過！")
    sys.exit(0)


if __name__ == "__main__":
    main()
