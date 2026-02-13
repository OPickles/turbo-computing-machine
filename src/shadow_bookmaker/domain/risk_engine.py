import math
from typing import Dict
from src.shadow_bookmaker.domain.models import CustomerTicket, RiskDecision, OddsDTO
from src.shadow_bookmaker.domain.ledger import GlobalLedger

class RiskEngine:
    def __init__(self, ledger: GlobalLedger, max_global_liability: float = 30000.0, min_house_edge: float = -0.05):
        self.ledger = ledger
        # ⚠️ 系统红线升级：单场比赛【全局最高承受】 3 万净亏损
        self.max_global_liability = max_global_liability 
        self.min_house_edge = min_house_edge

    def _calculate_true_prob(self, market_odds: OddsDTO, selection: str) -> float:
        p_home = 1.0 / market_odds.home_odds; p_away = 1.0 / market_odds.away_odds
        p_draw = 1.0 / (market_odds.draw_odds or 1.0) if market_odds.draw_odds else 0.0
        margin = p_home + p_away + p_draw
        if selection == "home": return p_home / margin
        elif selection == "away": return p_away / margin
        return p_draw / margin
        
    def _get_sharp_odds(self, market_odds: OddsDTO, selection: str) -> float:
        if selection == "home": return market_odds.home_odds
        elif selection == "away": return market_odds.away_odds
        return market_odds.draw_odds or 0.0

    def evaluate(self, ticket: CustomerTicket, sharp_market: Dict[str, OddsDTO]) -> RiskDecision:
        combined_true_prob = 1.0
        leg_details = []

        for leg in ticket.legs:
            if leg.match_id not in sharp_market: return self._reject(ticket, 0, 0, f"缺失外盘数据: {leg.match_id}")
            market = sharp_market[leg.match_id]
            sharp_odds = self._get_sharp_odds(market, leg.selection)
            true_prob = self._calculate_true_prob(market, leg.selection)
            combined_true_prob *= true_prob
            leg_details.append({"leg": leg, "sharp_odds": sharp_odds, "true_prob": true_prob})

        house_ev = 1.0 - (combined_true_prob * ticket.total_odds)
        if house_ev < self.min_house_edge: 
            return self._reject(ticket, house_ev, combined_true_prob, f"毒药单拦截。庄家期望: {house_ev*100:.1f}%")

        # 将风险等效映射到最容易打出的那条“危险腿”上进行账本测算
        danger_leg_info = max(leg_details, key=lambda x: x["true_prob"])
        danger_leg = danger_leg_info["leg"]
        sharp_odds = danger_leg_info["sharp_odds"]

        # 🎯 沙盘推演：假设全额吃下这笔单，全局盈亏矩阵会怎样？
        simulated_state = self.ledger.simulate_bet(danger_leg.match_id, danger_leg.selection, ticket.stake, ticket.liability)
        
        # 最坏情况：无论真实世界打出主、客、平，我们在矩阵里会面临的最大亏损 (通常是负数)
        future_worst_case = min(simulated_state.values())

        # 情况 1：未击穿全局防爆仓红线
        if future_worst_case >= -self.max_global_liability:
            return RiskDecision(
                ticket_id=ticket.ticket_id, action="ACCEPT_B_BOOK",
                reason=f"全局水位安全。吃下后本场最坏盈亏为 ¥{future_worst_case:.0f} (未破 ¥-{self.max_global_liability} 红线)。全吃入库。",
                house_ev=house_ev, true_probability=combined_true_prob, b_book_stake=ticket.stake,
                retained_stake=ticket.stake, retained_liability=ticket.liability,
                danger_match_id=danger_leg.match_id, danger_selection=danger_leg.selection
            )
            
        # 🚨 情况 2：溢出红线！触发智能泄洪，去外网抛盘对冲！
        excess_liability = abs(future_worst_case) - self.max_global_liability
        
        # 精确计算：去大盘抛出多少注码，赢回来的钱能正好填平这个超出的窟窿
        hedge_stake = math.ceil((excess_liability / (sharp_odds - 1.0)) / 50.0) * 50.0
        
        # 数学剥离：剥掉外围抛盘对冲的部分后，真正截留在自己底仓的本金和负债
        retained_stake = ticket.stake - hedge_stake
        retained_liability = ticket.liability - hedge_stake * (sharp_odds - 1.0)

        action = "ACCEPT_PARTIAL_HEDGE" if retained_stake > 0 else "ACCEPT_A_BOOK_HEDGE"

        return RiskDecision(
            ticket_id=ticket.ticket_id, action=action,
            reason=f"⚠️ 击穿警告！吃下此单最坏盈亏达 ¥{future_worst_case:.0f}。启动降维对冲以削减敞口。",
            house_ev=house_ev, true_probability=combined_true_prob, 
            hedge_stake=hedge_stake, hedge_odds=sharp_odds, b_book_stake=max(0.0, retained_stake),
            retained_stake=retained_stake, retained_liability=retained_liability,
            danger_match_id=danger_leg.match_id, danger_selection=danger_leg.selection
        )

    def _reject(self, ticket: CustomerTicket, ev: float, prob: float, reason: str) -> RiskDecision:
        return RiskDecision(ticket_id=ticket.ticket_id, action="REJECT", reason=reason, house_ev=ev, true_probability=prob)