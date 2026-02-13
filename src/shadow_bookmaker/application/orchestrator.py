from typing import List, Dict
from src.shadow_bookmaker.domain.risk_engine import RiskEngine
from src.shadow_bookmaker.domain.models import CustomerTicket, RiskDecision, OddsDTO
from src.shadow_bookmaker.application.team_mapper import TeamMapper
from src.shadow_bookmaker.infrastructure.bookmakers.mock_bookies import PinnacleMock

class BrokerOrchestrator:
    def __init__(self):
        self.mapper = TeamMapper()
        self.risk_engine = RiskEngine(max_liability_per_ticket=20000.0) # 设最高风控线两万
        self.pinnacle = PinnacleMock(self.mapper) # 必须有一个标杆大庄作为概率锚点
        
    async def evaluate_incoming_tickets(self, tickets: List[CustomerTicket]) -> List[RiskDecision]:
        odds_list = await self.pinnacle.fetch_odds()
        market_data: Dict[str, OddsDTO] = {}
        for odds in odds_list: market_data[odds.match_id] = odds
            
        decisions = []
        for ticket in tickets:
            decision = self.risk_engine.evaluate(ticket, market_data)
            decisions.append(decision)
            
        return decisions