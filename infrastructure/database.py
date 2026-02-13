import sqlite3
import os
from typing import Dict, List

# 将数据库文件建在根目录下的 data 文件夹中
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/shadow_vault.db"))

class DatabaseManager:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化两张核心金融表：大账本表(ledger_pnl) 和 历史订单流水表(order_book)"""
        with sqlite3.connect(DB_PATH) as conn:
            # 1. 全局水池表 (记录当前敞口水位)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ledger_pnl (
                    match_id TEXT PRIMARY KEY,
                    home REAL DEFAULT 0.0,
                    draw REAL DEFAULT 0.0,
                    away REAL DEFAULT 0.0
                )
            """)
            # 2. 审计溯源订单表 (记录每一笔风控放行的单子)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS order_book (
                    ticket_id TEXT PRIMARY KEY,
                    ticket_type TEXT,
                    stake REAL,
                    action TEXT,
                    retained_liability REAL,
                    hedge_stake REAL,
                    danger_match_id TEXT,
                    danger_selection TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
    def load_ledger(self) -> Dict[str, Dict[str, float]]:
        """系统重启时，瞬间从硬盘拉取水池现状"""
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM ledger_pnl").fetchall()
            return {r["match_id"]: {"home": r["home"], "draw": r["draw"], "away": r["away"]} for r in rows}

    def save_ledger_state(self, match_id: str, state: Dict[str, float]):
        """水池发生变动，利用 UPSERT 语法强制落盘保存"""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO ledger_pnl (match_id, home, draw, away)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(match_id) DO UPDATE SET
                home=excluded.home, draw=excluded.draw, away=excluded.away
            """, (match_id, state["home"], state["draw"], state["away"]))

    def save_ticket(self, ticket_id: str, ticket_type: str, stake: float, action: str, retained_liability: float, hedge_stake: float, danger_match_id: str, danger_selection: str):
        """留痕审计：将通过风控的单据永久存档为交易流水"""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO order_book (ticket_id, ticket_type, stake, action, retained_liability, hedge_stake, danger_match_id, danger_selection)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ticket_id, ticket_type, stake, action, retained_liability, hedge_stake, danger_match_id, danger_selection))
            
    def get_order_book(self) -> List[dict]:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM order_book ORDER BY timestamp DESC LIMIT 100").fetchall()
            return [dict(r) for r in rows]
            
    def clear_all(self):
        """次日清算删库指令"""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM ledger_pnl")
            conn.execute("DELETE FROM order_book")