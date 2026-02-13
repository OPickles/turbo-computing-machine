import math
from typing import Dict, List
from src.shadow_bookmaker.domain.models import CustomerTicket, RiskDecision, OddsDTO, TicketLeg

class RiskEngine:
    def __init__(self, max_liability_per_ticket: float = 20000.0, min_house_edge: float = 0.02):
        self.max_liability = max_liability_per_ticket
        self.min_house_edge = min_house_edge

    def _calculate_true_prob(self, market_odds: OddsDTO, selection: str) -> float:
        p_home = 1.0 / market_odds.home_odds
        p_away = 1.0 / market_odds.away_odds
        p_draw = 1.0 / market_odds.draw_odds if market_odds.draw_odds else 0.0
        margin = p_home + p_away + p_draw
        if selection == "home": return p_home / margin
        if selection == "away": return p_away / margin
        if selection == "draw": return p_draw / margin
        return 0.0
        
    def _get_sharp_odds(self, market_odds: OddsDTO, selection: str) -> float:
        if selection == "home": return market_odds.home_odds
        if selection == "away": return market_odds.away_odds
        if selection == "draw": return market_odds.draw_odds or 0.0
        return 0.0

    def evaluate(self, ticket: CustomerTicket, sharp_market: Dict[str, OddsDTO]) -> RiskDecision:
        combined_true_prob = 1.0
        leg_details = []

        for leg in ticket.legs:
            if leg.match_id not in sharp_market:
                return self._reject(ticket, 0, 0, f"缺失外盘数据: {leg.match_id}")
            sharp_odds_data = sharp_market[leg.match_id]
            sharp_odds = self._get_sharp_odds(sharp_odds_data, leg.selection)
            true_prob = self._calculate_true_prob(sharp_odds_data, leg.selection)
            
            combined_true_prob *= true_prob
            leg_details.append({"match_id": leg.match_id, "selection": leg.selection, "sharp_odds": sharp_odds, "true_prob": true_prob})

        house_ev = 1.0 - (combined_true_prob * ticket.total_odds)
        
        # 1. 毒药防守
        if house_ev < -0.05: 
            return self._reject(ticket, house_ev, combined_true_prob, f"毒药单！客户胜率({combined_true_prob*100:.1f}%)配合此赔率，庄家长期必亏。")

        # 2. 优质单敞口管理 (红线内硬吃)
        liability = ticket.liability
        if liability <= self.max_liability:
            return RiskDecision(
                ticket_id=ticket.ticket_id, action="ACCEPT_B_BOOK",
                reason=f"优质散户单。庄家长期优势 {house_ev*100:.1f}%，爆冷净亏损(¥{liability:.0f})在安全线内，直接硬吃对赌。",
                house_ev=house_ev, true_probability=combined_true_prob, b_book_stake=ticket.stake
            )
            
        # 3. 超出红线，启动高级对冲
        excess_liability = liability - self.max_liability
        
        if len(ticket.legs) == 1:
            sharp_odds = leg_details[0]["sharp_odds"]
            hedge_stake = math.ceil((excess_liability / (sharp_odds - 1.0)) / 50.0) * 50.0
            return RiskDecision(
                ticket_id=ticket.ticket_id, action="ACCEPT_PARTIAL_HEDGE",
                reason=f"单关敞口爆表(超标 ¥{excess_liability:.0f})。启动同赛道大盘对冲。",
                house_ev=house_ev, true_probability=combined_true_prob, hedge_stake=hedge_stake, hedge_odds=sharp_odds, b_book_stake=ticket.stake - hedge_stake
            )
        else:
            # 🎯 架构师绝招：二串一 断腿对冲 (Leg-breaker Hedge)
            danger_leg = max(leg_details, key=lambda x: x["true_prob"])
            hedge_stake = math.ceil((excess_liability / (danger_leg["sharp_odds"] - 1.0)) / 50.0) * 50.0
            
            return RiskDecision(
                ticket_id=ticket.ticket_id, action="ACCEPT_PARTIAL_HEDGE",
                reason=f"串关负债爆表！启动【断腿对冲】: 去大盘重注【单买】此串中最危险的一腿({danger_leg['match_id']} - {danger_leg['selection']})。若该腿打出，单关收米补坑；若该腿断了，客户串子报废，通杀本金。",
                house_ev=house_ev, true_probability=combined_true_prob, hedge_stake=hedge_stake, hedge_odds=danger_leg["sharp_odds"], b_book_stake=ticket.stake
            )

    def _reject(self, ticket: CustomerTicket, ev: float, prob: float, reason: str) -> RiskDecision:
        return RiskDecision(ticket_id=ticket.ticket_id, action="REJECT", reason=reason, house_ev=ev, true_probability=prob)