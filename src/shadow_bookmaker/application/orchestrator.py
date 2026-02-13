import asyncio
from typing import List, Dict
from src.shadow_bookmaker.domain.risk_engine import RiskEngine
from src.shadow_bookmaker.domain.ledger import GlobalLedger
from src.shadow_bookmaker.domain.models import CustomerTicket, RiskDecision, OddsDTO
from src.shadow_bookmaker.application.team_mapper import TeamMapper
from src.shadow_bookmaker.infrastructure.bookmakers.mock_bookies import PinnacleMock
from src.shadow_bookmaker.infrastructure.database import DatabaseManager

class BrokerOrchestrator:
    def __init__(self):
        self.mapper = TeamMapper()
        # 🌍 挂载真实数据库，注入账本
        self.db = DatabaseManager()
        self.ledger = GlobalLedger(self.db) 
        self.risk_engine = RiskEngine(ledger=self.ledger, max_global_liability=30000.0)
        self.pinnacle = PinnacleMock(self.mapper)
        
    async def evaluate_incoming_tickets(self, tickets: List[CustomerTicket]) -> List[RiskDecision]:
        odds_list = await self.pinnacle.fetch_odds()
        market_data: Dict[str, OddsDTO] = {odds.match_id: odds for odds in odds_list}
        return [self.risk_engine.evaluate(ticket, market_data) for ticket in tickets]

    def commit_decision(self, decision: RiskDecision, ticket: CustomerTicket):
        """签字入库：记账 + 存档 (留痕双保险)"""
        if decision.action in ["ACCEPT_B_BOOK", "ACCEPT_PARTIAL_HEDGE", "ACCEPT_A_BOOK_HEDGE"]:
            # 1. 资金水池更新
            self.ledger.commit_bet(
                decision.danger_match_id, decision.danger_selection, 
                decision.retained_stake, decision.retained_liability
            )
            # 2. 单据永久存档入库
            self.db.save_ticket(
                ticket_id=ticket.ticket_id, ticket_type=ticket.ticket_type,
                stake=ticket.stake, action=decision.action,
                retained_liability=decision.retained_liability, hedge_stake=decision.hedge_stake,
                danger_match_id=decision.danger_match_id, danger_selection=decision.danger_selection
            )
            
    def wipe_all_data(self):
        self.db.clear_all()
        self.ledger.pl_states.clear()