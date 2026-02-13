from collections import defaultdict
from typing import Dict
from src.shadow_bookmaker.infrastructure.database import DatabaseManager

class GlobalLedger:
    def __init__(self, db: DatabaseManager):
        self.db = db
        # ⚡ 核心进化：系统启动时直接从本地物理硬盘恢复水池状态！
        self.pl_states = defaultdict(lambda: {"home": 0.0, "away": 0.0, "draw": 0.0})
        self.pl_states.update(self.db.load_ledger())

    def simulate_bet(self, match_id: str, selection: str, stake: float, liability: float) -> Dict[str, float]:
        """沙盘推演：在内存中极速计算，不写硬盘"""
        current_state = self.pl_states[match_id].copy()
        for outcome in ["home", "away", "draw"]:
            if outcome == selection: current_state[outcome] -= liability
            else: current_state[outcome] += stake
        return current_state

    def commit_bet(self, match_id: str, selection: str, stake: float, liability: float):
        """核心动作：确认接单后，更新内存的同时，立刻写死到物理硬盘"""
        new_state = self.simulate_bet(match_id, selection, stake, liability)
        self.pl_states[match_id] = new_state
        self.db.save_ledger_state(match_id, new_state)

    def get_all_exposures(self):
        return dict(self.pl_states)