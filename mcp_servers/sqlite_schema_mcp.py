#!/usr/bin/env python3
"""
真實可執行的 SQLite Schema MCP Server (mcp_servers/sqlite_schema_mcp.py)
支援標準 Model Context Protocol (MCP) JSON-RPC 2.0 over Stdio 傳輸協議。
提供兩個核心工具供 Agy 2.0 Headless Agent 呼叫：
1. list_tables: 列出生產環境資料庫中的所有資料表
2. get_table_schema: 取得指定資料表的真實欄位定義與約束條件，並比對 SQL 語句中的欄位是否存在
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


class SQLiteSchemaMCPServer:
    def __init__(self, schema_sql_path: str) -> None:
        self.schema_sql_path = Path(schema_sql_path)
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        if self.schema_sql_path.exists():
            self.conn.executescript(self.schema_sql_path.read_text(encoding="utf-8"))
            self.conn.commit()

    def list_tables(self) -> List[str]:
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return [r["name"] for r in rows]

    def get_table_schema(self, table_name: str, check_columns: List[str] | None = None) -> Dict[str, Any]:
        cur = self.conn.cursor()
        # 驗證表名合法性
        tables = self.list_tables()
        if table_name not in tables:
            return {"error": f"資料表 `{table_name}` 不存在。現有資料表：{tables}"}

        pragma_rows = cur.execute(f"PRAGMA table_info({table_name})").fetchall()
        columns = [
            {
                "name": r["name"],
                "type": r["type"],
                "notnull": bool(r["notnull"]),
                "default_value": r["dflt_value"],
                "is_pk": bool(r["pk"]),
            }
            for r in pragma_rows
        ]
        actual_col_names = {c["name"] for c in columns}

        ddl_row = cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        ).fetchone()

        result: Dict[str, Any] = {
            "table_name": table_name,
            "columns": columns,
            "ddl": ddl_row["sql"] if ddl_row else "",
        }

        if check_columns:
            missing_cols = [c for c in check_columns if c not in actual_col_names]
            result["checked_columns"] = check_columns
            result["missing_or_invalid_columns"] = missing_cols
            result["schema_match"] = len(missing_cols) == 0

        return result

    def handle_rpc(self, request: Dict[str, Any]) -> Dict[str, Any] | None:
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "sqlite-schema-mcp", "version": "1.0.0"},
                },
            }
        elif method == "notifications/initialized":
            return None
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "list_tables",
                            "description": "List all database tables defined in the production schema.",
                            "inputSchema": {"type": "object", "properties": {}},
                        },
                        {
                            "name": "get_table_schema",
                            "description": "Get exact column names, types, and DDL of a table, and optionally verify if a list of column names exist in that table.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "table_name": {"type": "string", "description": "Name of the table (e.g., orders, payments)"},
                                    "check_columns": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Optional list of columns used in code to verify against actual schema",
                                    },
                                },
                                "required": ["table_name"],
                            },
                        },
                    ]
                },
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})
            if tool_name == "list_tables":
                data = {"tables": self.list_tables()}
            elif tool_name == "get_table_schema":
                data = self.get_table_schema(
                    args.get("table_name", ""),
                    args.get("check_columns"),
                )
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
                }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]
                },
            }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not supported: {method}"},
        }


def main() -> None:
    root_dir = Path(__file__).resolve().parent.parent
    default_schema = root_dir / "src" / "db" / "schema.sql"
    schema_path = os.environ.get("SCHEMA_SQL_PATH", str(default_schema))
    server = SQLiteSchemaMCPServer(schema_path)

    # 支援命令列快速自檢模式 (--self-test)，方便 CI 流水線直接驗證 MCP 工具
    if "--self-test" in sys.argv:
        test_res = server.get_table_schema(
            "payments",
            check_columns=["payment_id", "order_id", "total_price", "payment_method", "card_cvv", "status"],
        )
        print(json.dumps(test_res, ensure_ascii=False, indent=2))
        return

    # 標準 Stdio JSON-RPC 迴圈
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = server.handle_rpc(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except Exception as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": str(exc)},
            }
            sys.stdout.write(json.dumps(err_resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
