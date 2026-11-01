#!/usr/bin/env python3
"""
Skill 附帶的確定性靜態掃描工具 (.agents/skills/payment-security-audit/scripts/ast_pci_scanner.py)
結合正規表達式與 Python AST 抽象語法樹，掃描目標檔案是否違反 GEMINI.md 規範。
"""

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


SECRET_PATTERNS = [
    (r"sk_live_[0-9a-zA-Z]{10,}", "Hardcoded Stripe Live Secret Key (sk_live_*)"),
    (r"AIza[0-9A-Za-z\-_]{35}", "Hardcoded Google API Key"),
    (r"(?i)(api_key|secret|password)\s*=\s*['\"][^'\"]{8,}['\"]", "Suspicious Hardcoded Credential"),
]

PCI_VIOLATION_PATTERNS = [
    (r"\bcard_cvv\b|\bcvv\b", "PCI-DSS Req 3.2 Violation: Handling or storing card CVV/CVC code"),
]


class SecurityASTVisitor(ast.NodeVisitor):
    def __init__(self, filename: str, lines: List[str]) -> None:
        self.filename = filename
        self.lines = lines
        self.findings: List[Dict[str, Any]] = []

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        """偵測 f-string 是否用於組裝 SQL 語句"""
        raw_line = self.lines[node.lineno - 1] if 0 < node.lineno <= len(self.lines) else ""
        sql_keywords = ("SELECT ", "INSERT INTO ", "UPDATE ", "DELETE FROM ")
        if any(kw in raw_line.upper() for kw in sql_keywords):
            self.findings.append({
                "rule_id": "SEC-SQLI-001",
                "severity": "critical",
                "file": self.filename,
                "line": node.lineno,
                "problem": "使用 Python f-string 直接拼接 SQL 語句，導致嚴重的 SQL Injection 注入風險。",
                "fix": "改用參數化查詢佔位符 `?`，例如 `cursor.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,))`。",
            })
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """偵測金額相關函數是否誤用 float 型別註解"""
        for arg in node.args.args:
            if any(k in arg.arg.lower() for k in ("price", "amount", "fee", "discount")):
                if isinstance(arg.annotation, ast.Name) and arg.annotation.id == "float":
                    self.findings.append({
                        "rule_id": "FIN-TYPE-001",
                        "severity": "warning",
                        "file": self.filename,
                        "line": node.lineno,
                        "problem": f"函數 `{node.name}` 的參數 `{arg.arg}` 使用 `float` 處理金融金額，可能產生 IEEE 754 浮點數精度誤差。",
                        "fix": "依據 GEMINI.md 規範，金額欄位應統一改用整數分（`amount_cents: int`）或 `decimal.Decimal`。",
                    })
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        """偵測迴圈內是否呼叫 cursor.execute 造成 N+1 Query"""
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                if child.func.attr == "execute":
                    self.findings.append({
                        "rule_id": "PERF-NPLUS1-001",
                        "severity": "suggestion",
                        "file": self.filename,
                        "line": child.lineno,
                        "problem": "在 `for` 迴圈內部逐筆執行資料庫 `cursor.execute()`，在訂單量大時將引發 N+1 查詢效能瓶頸。",
                        "fix": "改用 `LEFT JOIN` 或 `WHERE order_id IN (...)` 批次查詢。",
                    })
        self.generic_visit(node)


def scan_file(file_path: Path, base_dir: Path) -> List[Dict[str, Any]]:
    rel_path = file_path.relative_to(base_dir).as_posix()
    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    findings: List[Dict[str, Any]] = []

    # 1. Regex 掃描硬編碼金鑰與 PCI-DSS CVV 違規
    for idx, line in enumerate(lines, start=1):
        if line.strip().startswith("#"):
            continue
        for pattern, desc in SECRET_PATTERNS:
            if re.search(pattern, line):
                findings.append({
                    "rule_id": "SEC-SECRET-001",
                    "severity": "critical",
                    "file": rel_path,
                    "line": idx,
                    "problem": f"偵測到硬編碼敏感憑證 ({desc})，一旦推送至版本控制庫將造成嚴重資安洩漏。",
                    "fix": "移除明文金鑰，改用 `os.environ['STRIPE_API_SECRET']` 並於 CI Secrets 注入。",
                })
                break

        for pattern, desc in PCI_VIOLATION_PATTERNS:
            if re.search(pattern, line) and "INSERT INTO" in line.upper():
                findings.append({
                    "rule_id": "PCI-DSS-3.2",
                    "severity": "critical",
                    "file": rel_path,
                    "line": idx,
                    "problem": f"違反 PCI-DSS 第 3.2 條規範 ({desc})，嘗試將信用卡安全碼 `card_cvv` 寫入資料庫。",
                    "fix": "立即從函數參數與 SQL `INSERT` 語句中移除 `card_cvv`，前端應透過 Stripe Tokenization 處理。",
                })

    # 2. AST 語法樹深度掃描
    try:
        tree = ast.parse(content, filename=rel_path)
        visitor = SecurityASTVisitor(rel_path, lines)
        visitor.visit(tree)
        findings.extend(visitor.findings)
    except SyntaxError as e:
        findings.append({
            "rule_id": "SYNTAX-ERR",
            "severity": "critical",
            "file": rel_path,
            "line": e.lineno or 1,
            "problem": f"Python 語法錯誤: {e.msg}",
            "fix": "修正語法錯誤後重新執行掃描。",
        })

    return findings


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("src")
    base_dir = Path.cwd()
    if not target.is_absolute():
        target = base_dir / target

    py_files = [target] if target.is_file() else list(target.rglob("*.py"))
    all_findings: List[Dict[str, Any]] = []
    for f in sorted(py_files):
        all_findings.extend(scan_file(f, base_dir))

    output = {
        "scanner": "ast_pci_scanner v1.0",
        "scanned_files": len(py_files),
        "total_findings": len(all_findings),
        "findings": all_findings,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
