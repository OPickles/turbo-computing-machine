import asyncio
from typing import List, Dict
from src.shadow_bookmaker.domain.risk_engine import RiskEngine
from src.shadow_bookmaker.domain.ledger import GlobalLedger
from src.shadow_bookmaker.domain.models import CustomerTicket, RiskDecision, OddsDTO
from src.shadow_bookmaker.application.team_mapper import TeamMapper
from src.shadow_bookmaker.infrastructure.bookmakers.mock_bookies import PinnacleMock

class BrokerOrchestrator:
    # 🌍 核心突破：初始化唯一的全局大账本注入
    def __init__(self, ledger: GlobalLedger):
        self.mapper = TeamMapper()
        self.ledger = ledger 
        self.risk_engine = RiskEngine(ledger=self.ledger, max_global_liability=30000.0)
        self.pinnacle = PinnacleMock(self.mapper)
        
    async def evaluate_incoming_tickets(self, tickets: List[CustomerTicket]) -> List[RiskDecision]:
        odds_list = await self.pinnacle.fetch_odds()
        market_data: Dict[str, OddsDTO] = {odds.match_id: odds for odds in odds_list}
            
        decisions = []
        for ticket in tickets:
            decisions.append(self.risk_engine.evaluate(ticket, market_data))
        return decisions

    def commit_decision(self, decision: RiskDecision):
        """签字入库：将剥离对冲后截留的真实风险落定大账本"""
        if decision.action in ["ACCEPT_B_BOOK", "ACCEPT_PARTIAL_HEDGE", "ACCEPT_A_BOOK_HEDGE"]:
            self.ledger.commit_bet(
                decision.danger_match_id, decision.danger_selection, 
                decision.retained_stake, decision.retained_liability
            )