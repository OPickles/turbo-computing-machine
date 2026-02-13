import asyncio
import time
from typing import List, Dict
from src.shadow_bookmaker.domain.risk_engine import RiskEngine
from src.shadow_bookmaker.domain.ledger import GlobalLedger
from src.shadow_bookmaker.domain.models import CustomerTicket, RiskDecision, OddsDTO
from src.shadow_bookmaker.application.team_mapper import TeamMapper
from src.shadow_bookmaker.infrastructure.database import DatabaseManager
from src.shadow_bookmaker.infrastructure.bookmakers.mock_bookies import PinnacleMock

# 🔌 拔掉玩具插头，准备接入真实雷达！
from src.shadow_bookmaker.infrastructure.bookmakers.the_odds_api import TheOddsAPIBookmaker
from src.shadow_bookmaker.config import settings

class BrokerOrchestrator:
    def __init__(self):
        self.mapper = TeamMapper()
        self.db = DatabaseManager()
        self.ledger = GlobalLedger(self.db) 
        self.risk_engine = RiskEngine(ledger=self.ledger, max_global_liability=30000.0)
        
        # 智能双擎：有钥匙开超跑，没钥匙骑自行车
        if settings.ODDS_API_KEY:
            self.pinnacle = TheOddsAPIBookmaker(self.mapper)
        else:
            self.pinnacle = PinnacleMock(self.mapper)
            
        # 🛡️ 架构师防御手段：60秒极速缓存墙
        self._market_cache: Dict[str, OddsDTO] = {}
        self._last_fetch_time = 0

    async def get_live_market(self, force_refresh=False) -> Dict[str, OddsDTO]:
        """抓取外网数据（即使你1秒内点100次，它也只会在满60秒后才真正去外网抓取，其余时间读内存极速返回）"""
        if force_refresh or not self._market_cache or (time.time() - self._last_fetch_time > 60):
            odds_list = await self.pinnacle.fetch_odds()
            if odds_list:
                self._market_cache = {odds.match_id: odds for odds in odds_list}
                self._last_fetch_time = time.time()
        return self._market_cache
        
    async def evaluate_incoming_tickets(self, tickets: List[CustomerTicket]) -> List[RiskDecision]:
        market_data = await self.get_live_market()
        return [self.risk_engine.evaluate(ticket, market_data) for ticket in tickets]

    def commit_decision(self, decision: RiskDecision, ticket: CustomerTicket):
        if decision.action in ["ACCEPT_B_BOOK", "ACCEPT_PARTIAL_HEDGE", "ACCEPT_A_BOOK_HEDGE"]:
            self.ledger.commit_bet(decision.danger_match_id, decision.danger_selection, decision.retained_stake, decision.retained_liability)
            self.db.save_ticket(ticket.ticket_id, ticket.ticket_type, ticket.stake, decision.action, decision.retained_liability, decision.hedge_stake, decision.danger_match_id, decision.danger_selection)
            
    def wipe_all_data(self):
        self.db.clear_all()
        self.ledger.pl_states.clear()