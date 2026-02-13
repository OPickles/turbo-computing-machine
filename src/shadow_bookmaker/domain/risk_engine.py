import math
from typing import Dict
from src.shadow_bookmaker.domain.models import CustomerTicket, RiskDecision, OddsDTO

class RiskEngine:
    def __init__(self, max_liability_per_ticket: float = 20000.0, min_house_edge: float = 0.02):
        # 单张票我们最多愿意承受多大的净赔付风险 (例如 2万元)
        self.max_liability = max_liability_per_ticket
        # 我们期望客户的单子至少自带 2% 的劣势，我们才吃下
        self.min_house_edge = min_house_edge

    def _calculate_true_prob(self, market_odds: OddsDTO, selection: str) -> float:
        """核心数学1：剥离大盘抽水，还原真实胜率 (Margin Proportional 方法)"""
        p_home = 1.0 / market_odds.home_odds
        p_away = 1.0 / market_odds.away_odds
        p_draw = 1.0 / market_odds.draw_odds if market_odds.draw_odds else 0.0
        
        margin = p_home + p_away + p_draw # 必定 > 1.0
        
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
        combined_sharp_odds = 1.0
        
        for leg in ticket.legs:
            if leg.match_id not in sharp_market:
                return self._reject(ticket, 0, 0, f"缺失外部大盘基准数据: {leg.match_id}")
            
            sharp_odds_data = sharp_market[leg.match_id]
            sharp_odds = self._get_sharp_odds(sharp_odds_data, leg.selection)
            
            if sharp_odds <= 1.0:
                 return self._reject(ticket, 0, 0, f"大盘未开盘或已关盘: {leg.match_id}")
                 
            combined_sharp_odds *= sharp_odds
            combined_true_prob *= self._calculate_true_prob(sharp_odds_data, leg.selection)

        # 核心算式：庄家期望收益 (House EV)。>0说明我们在赢钱。
        house_ev = 1.0 - (combined_true_prob * ticket.total_odds)
        
        # ================== 决 策 树 ================== #
        
        # 决策 1：纯粹的无风险套利 (A-Book)
        if combined_sharp_odds > ticket.total_odds:
            # 客户要的赔率居然比外围大盘还低。直接去外围反向下注，空手套白狼赚差价。
            raw_hedge_stake = ticket.potential_payout / combined_sharp_odds
            actual_hedge_stake = math.ceil(raw_hedge_stake / 50.0) * 50.0 # 向上取整到50，防止大盘查机器人
            
            profit = ticket.stake - actual_hedge_stake
            if profit > 0:
                return RiskDecision(
                    ticket_id=ticket.ticket_id, action="ACCEPT_A_BOOK_HEDGE",
                    reason=f"存在无风险利差！客户赔率({ticket.total_odds:.2f}) < 大盘赔率({combined_sharp_odds:.2f})。锁定无风险净赚 ¥{profit:.0f}。",
                    house_ev=house_ev, true_probability=combined_true_prob,
                    hedge_stake=actual_hedge_stake, hedge_odds=combined_sharp_odds, b_book_stake=0
                )

        # 决策 2：毒药防守 (客户占优势)
        if house_ev < 0:
            return self._reject(ticket, house_ev, combined_true_prob, f"毒流警告！客户胜率({combined_true_prob*100:.1f}%)配上他要的赔率，庄家处于极度劣势。")

        # 决策 3：优质韭菜单的敞口管理 (B-Book vs Partial Hedge)
        liability = ticket.liability
        
        if liability <= self.max_liability:
            # 风险在承受范围内，全仓吃下
            return RiskDecision(
                ticket_id=ticket.ticket_id, action="ACCEPT_B_BOOK",
                reason=f"完美散户单。庄家长期优势 {house_ev*100:.1f}%，万一爆冷赔付金额(¥{liability:.0f})也在安全线内，直接吃飞对赌。",
                house_ev=house_ev, true_probability=combined_true_prob, b_book_stake=ticket.stake
            )
        else:
            # 超过了最大承受极限，必须切掉一刀去大盘对冲保命
            excess_liability = liability - self.max_liability
            raw_hedge_stake = excess_liability / (combined_sharp_odds - 1.0)
            hedge_stake = math.ceil(raw_hedge_stake / 50.0) * 50.0
            
            b_book_stake = ticket.stake - hedge_stake
            
            return RiskDecision(
                ticket_id=ticket.ticket_id, action="ACCEPT_PARTIAL_HEDGE",
                reason=f"优质单但敞口爆表 (可能亏损 ¥{liability:.0f} > 红线 ¥{self.max_liability})。截留吃下本金 ¥{b_book_stake:.0f}，溢出风险抛向大盘。",
                house_ev=house_ev, true_probability=combined_true_prob,
                hedge_stake=hedge_stake, hedge_odds=combined_sharp_odds, b_book_stake=b_book_stake
            )

    def _reject(self, ticket: CustomerTicket, ev: float, prob: float, reason: str) -> RiskDecision:
        return RiskDecision(ticket_id=ticket.ticket_id, action="REJECT", reason=reason, house_ev=ev, true_probability=prob)