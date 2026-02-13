from typing import List, Optional
from src.shadow_bookmaker.domain.models import OddsDTO, ArbitrageOpportunity

class ArbitrageCalculator:
    @staticmethod
    def calculate_2way(odds_list: List[OddsDTO], total_capital: float = 1000.0) -> Optional[ArbitrageOpportunity]:
        if not odds_list or len(odds_list) < 2: return None
            
        best_home = max(odds_list, key=lambda x: x.home_odds)
        best_away = max(odds_list, key=lambda x: x.away_odds)
        
        # 同一庄家不可能产生真实套利，直接排除
        if best_home.bookmaker == best_away.bookmaker:
            return None

        # 核心公式：隐含概率之和
        implied_prob = (1 / best_home.home_odds) + (1 / best_away.away_odds)
        
        # < 1.0 即说明水溢出了，存在无风险套利
        if implied_prob < 1.0:
            profit_margin = 1.0 - implied_prob
            
            # 基础资金分配 (保证双边收益绝对相等)
            stake_home = (total_capital / implied_prob) / best_home.home_odds
            stake_away = (total_capital / implied_prob) / best_away.away_odds
            
            return ArbitrageOpportunity(
                match_id=best_home.match_id,
                profit_margin=profit_margin,
                best_home_odds=best_home.home_odds,
                best_home_bookie=best_home.bookmaker,
                best_away_odds=best_away.away_odds,
                best_away_bookie=best_away.bookmaker,
                recommended_stakes={"home": stake_home, "away": stake_away},
                total_investment=total_capital
            )
        return None