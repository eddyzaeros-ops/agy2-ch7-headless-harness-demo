"""
電商訂單與支付處理模組 (src/order_service.py)
此檔案模擬開發者在 CL / PR 中提交的變更，包含數個供 Agy 2.0 Headless + 6 大 Harness 元素檢測的典型問題：
1. [CRITICAL] 硬編碼 Stripe 生產環境 Secret Key (違反 GEMINI.md 1.1)
2. [CRITICAL] SQL 注入漏洞：使用 f-string 直接拼接 order_id (違反 GEMINI.md 1.3)
3. [CRITICAL] 違反 PCI-DSS 規範：接收並嘗試將 card_cvv 寫入資料庫，且欄位 total_price 與真實 Schema (amount_cents) 不符 (由 MCP Server + Skill 檢出)
4. [WARNING] 使用 float 計算折扣後金額，可能產生浮點數誤差 (違反 GEMINI.md 2.1)
"""

import os
import sqlite3
import uuid
from typing import Any, Dict, List, Optional

# ❌ 問題 1 [CRITICAL]: 硬編碼敏感 API Secret Key
PAYMENT_GATEWAY_SECRET = "hardcoded_prod_secret_token_99887766"


class OrderPaymentService:
    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def init_db(self, schema_file: str) -> None:
        with open(schema_file, "r", encoding="utf-8") as f:
            self.conn.executescript(f.read())
        self.conn.commit()

    def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """查詢單筆訂單資訊"""
        cursor = self.conn.cursor()
        # ❌ 問題 2 [CRITICAL]: 使用 f-string 直接拼接 SQL，存在嚴重 SQL Injection 風險
        query = f"SELECT * FROM orders WHERE order_id = '{order_id}'"
        row = cursor.execute(query).fetchone()
        return dict(row) if row else None

    def calculate_discounted_amount(self, base_price: float, discount_rate: float) -> float:
        """計算折扣後金額"""
        # ❌ 問題 4 [WARNING]: 金融系統使用 float 浮點數計算金額，易出現 19.99 * 0.9 = 17.991000000000003 精度誤差
        return round(base_price * (1.0 - discount_rate), 2)

    def process_payment(
        self,
        order_id: str,
        total_price: float,
        card_number_last4: str,
        card_cvv: str,
    ) -> str:
        """處理訂單付款並寫入 payments 資料表"""
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        cursor = self.conn.cursor()

        # ❌ 問題 3 [CRITICAL]:
        # (a) 違反 PCI-DSS 儲存了 card_cvv
        # (b) 未對照 MCP 真實 Schema：payments 表實際欄位為 amount_cents (INTEGER)，並無 total_price 與 card_cvv 欄位！
        # (c) 再次使用 f-string 拼接 SQL
        insert_sql = (
            f"INSERT INTO payments (payment_id, order_id, total_price, payment_method, card_cvv, status) "
            f"VALUES ('{payment_id}', '{order_id}', {total_price}, 'CARD_{card_number_last4}', '{card_cvv}', 'PAID')"
        )
        cursor.execute(insert_sql)
        self.conn.commit()
        return payment_id

    def get_user_orders_with_payments(self, user_id: str) -> List[Dict[str, Any]]:
        """查詢使用者的所有訂單及其付款記錄"""
        cursor = self.conn.cursor()
        orders = cursor.execute(
            "SELECT * FROM orders WHERE user_id = ?", (user_id,)
        ).fetchall()

        results = []
        # ⚠️ 潛在 N+1 查詢問題：在迴圈內逐筆查詢 payments
        for o in orders:
            order_dict = dict(o)
            payments = cursor.execute(
                "SELECT * FROM payments WHERE order_id = ?", (o["order_id"],)
            ).fetchall()
            order_dict["payments"] = [dict(p) for p in payments]
            results.append(order_dict)
        return results
