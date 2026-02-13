from collections import defaultdict
from typing import Dict

class GlobalLedger:
    def __init__(self):
        # 结构: match_id -> { "home": 0.0, "away": 0.0, "draw": 0.0 }
        # 记录 PnL (盈亏矩阵)。正数 = 庄家白赚本金，负数 = 庄家面临赔付敞口
        self.pl_states: Dict[str, Dict[str, float]] = defaultdict(lambda: {"home": 0.0, "away": 0.0, "draw": 0.0})

    def simulate_bet(self, match_id: str, selection: str, stake: float, liability: float) -> Dict[str, float]:
        """沙盘推演：如果接下这笔敞口，全局账本的盈亏矩阵会变成什么样？"""
        current_state = self.pl_states[match_id].copy()
        
        for outcome in ["home", "away", "draw"]:
            if outcome == selection:
                # 客户押中，庄家需掏出利润赔付
                current_state[outcome] -= liability
            else:
                # 客户没押中，庄家白赚其本金
                current_state[outcome] += stake
                
        return current_state

    def commit_bet(self, match_id: str, selection: str, stake: float, liability: float):
        """核心动作：确认接单后，将敞口不可逆地记入总账本"""
        self.pl_states[match_id] = self.simulate_bet(match_id, selection, stake, liability)

    def get_all_exposures(self):
        return dict(self.pl_states)