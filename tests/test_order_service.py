"""
單元測試套件 (tests/test_order_service.py)
供 CI 流水線與 Stop Hook 驗證程式碼正確性與安全性
"""

import os
import unittest
from pathlib import Path
from src.order_service import OrderPaymentService


class TestOrderPaymentService(unittest.TestCase):
    def setUp(self) -> None:
        self.root_dir = Path(__file__).resolve().parent.parent
        self.schema_path = self.root_dir / "src" / "db" / "schema.sql"
        self.service = OrderPaymentService(":memory:")
        self.service.init_db(str(self.schema_path))
        self.service.conn.execute(
            "INSERT INTO orders (order_id, user_id, amount_cents, currency, status) VALUES (?, ?, ?, ?, ?)",
            ("ord_1001", "usr_01", 25000, "TWD", "PENDING"),
        )
        self.service.conn.commit()

    def test_get_order_by_id_normal(self) -> None:
        order = self.service.get_order_by_id("ord_1001")
        self.assertIsNotNone(order)
        assert order is not None
        self.assertEqual(order["amount_cents"], 25000)

    def test_sql_injection_resilience(self) -> None:
        """驗證查詢是否能抵禦 SQL Injection 攻擊載荷"""
        malicious_input = "' OR '1'='1"
        order = self.service.get_order_by_id(malicious_input)
        # 若使用參數化查詢，malicious_input 應找不到任何訂單 (None)
        # 若使用 f-string 拼接，則會回傳第一筆訂單，導致此測試失敗！
        self.assertIsNone(
            order,
            "偵測到 SQL Injection 漏洞！惡意輸入回傳了非預期的訂單資料。",
        )


if __name__ == "__main__":
    unittest.main()
