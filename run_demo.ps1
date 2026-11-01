# ==============================================================================
# Google Antigravity 2.0 (Agy 2.0) Headless & CL/CI 6-Harness 一鍵體驗腳本 (Windows PowerShell)
# 檔案路徑：e:\Antigravity 2\黃佳電子書\Ch7 工作區\run_demo.ps1
# ==============================================================================
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

Set-Location $PSScriptRoot

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " 🎯 Step 1: 測試 [Harness 5 - MCP Server] 查詢真實資料庫 Schema" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
python mcp_servers/sqlite_schema_mcp.py --self-test

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host " 🎯 Step 2: 測試 [Harness 6 - PreToolUse Hook] 攔截危險指令 (rm -rf / .env)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
'{"toolCall":{"name":"run_command","args":{"CommandLine":"cat .env && rm -rf /"}}}' | python scripts/hooks/pre_tool_security_guard.py

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host " 🎯 Step 3: 測試 [Harness 2 - Skill 靜態掃描器] AST + PCI-DSS 預檢" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
python .agents/skills/payment-security-audit/scripts/ast_pci_scanner.py src/

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host " 🎯 Step 4: 執行完整 [Agy 2.0 Headless 6-Harness 總編排器] 產出報告" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
python scripts/agy_sdk_headless_runner.py --gate-mode observer > $null
Write-Host "✅ 已產出 JSON 報告: reports/cl_review_report.json" -ForegroundColor Green
Write-Host "✅ 已產出 PR 評論檔: reports/pr_comment.md" -ForegroundColor Green
Write-Host "✅ 已寫入 Hook 審計日誌: logs/headless_hook_audit.jsonl" -ForegroundColor Green

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host " 🎯 Step 5: 模擬本地提交 CL (Pre-Commit Gate 門禁攔截展示)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
python scripts/local_cl_precommit_gate.py
Write-Host "📌 Pre-Commit Gate Exit Code: $LASTEXITCODE (非 0 代表成功攔截不合規的 CL 提交！)" -ForegroundColor Yellow
