#!/usr/bin/env python3
"""
Google Antigravity 2.0 (Agy 2.0) Headless & CL/CI 6-Harness 一鍵互動展示腳本
檔案路徑：e:\Antigravity 2\黃佳電子書\Ch7 工作區\run_demo.py
執行方式：python run_demo.py
"""

from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["PYTHONIOENCODING"] = "utf-8"
ROOT = Path(__file__).resolve().parent


def banner(title: str) -> None:
    print("\n" + "=" * 74)
    print(f" 🎯 {title}")
    print("=" * 74)


def main() -> None:
    # Step 1: MCP Server
    banner("Step 1: 驗證 [Harness 5 - MCP Server] 查詢真實資料庫 Schema")
    subprocess.run([sys.executable, "mcp_servers/sqlite_schema_mcp.py", "--self-test"], cwd=ROOT)

    # Step 2: PreToolUse Hook
    banner("Step 2: 驗證 [Harness 6 - PreToolUse Hook] 硬性攔截危險指令 (cat .env && rm -rf /)")
    bad_payload = json.dumps({"toolCall": {"name": "run_command", "args": {"CommandLine": "cat .env && rm -rf /"}}})
    proc = subprocess.run(
        [sys.executable, "scripts/hooks/pre_tool_security_guard.py"],
        input=bad_payload,
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=ROOT,
    )
    print(proc.stdout.strip())

    # Step 3: Skill AST Scanner
    banner("Step 3: 驗證 [Harness 2 - Skill] 執行 AST + PCI-DSS 確定性靜態掃描")
    subprocess.run(
        [sys.executable, ".agents/skills/payment-security-audit/scripts/ast_pci_scanner.py", "src/"],
        cwd=ROOT,
    )

    # Step 4: Full Headless 6-Harness Orchestrator
    banner("Step 4: 執行完整 [Agy 2.0 Headless 6-Harness 總編排器] 產出 JSON 與 PR 報告")
    subprocess.run(
        [sys.executable, "scripts/agy_sdk_headless_runner.py", "--gate-mode", "observer"],
        stdout=subprocess.DEVNULL,
        cwd=ROOT,
    )
    print("✅ 已產出結構化 JSON 報告 : reports/cl_review_report.json")
    print("✅ 已產出 PR 評論 Markdown : reports/pr_comment.md")
    print("✅ 已寫入 Hook 審計日誌   : logs/headless_hook_audit.jsonl")

    # Step 5: Local CL Pre-Commit Gate
    banner("Step 5: 模擬本地提交 CL (執行 Pre-Commit Gate 門禁攔截)")
    gate_proc = subprocess.run([sys.executable, "scripts/local_cl_precommit_gate.py"], cwd=ROOT)
    print(f"\n📌 Pre-Commit Gate Exit Code: {gate_proc.returncode} (Exit Code=1 代表成功攔截不合規的 CL 提交！)")


if __name__ == "__main__":
    main()
