from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class OddsDTO(BaseModel):
    bookmaker: str
    match_id: str
    home_team: str
    away_team: str
    home_odds: float = Field(gt=1.0)
    away_odds: float = Field(gt=1.0)
    draw_odds: Optional[float] = None

class TicketLeg(BaseModel):
    match_id: str
    selection: Literal["home", "away", "draw"]
    customer_odds: float

class CustomerTicket(BaseModel):
    ticket_id: str
    ticket_type: Literal["single", "parlay_2"]
    stake: float = Field(..., ge=1000, le=50000)
    legs: List[TicketLeg]
    
    @property
    def total_odds(self) -> float:
        res = 1.0
        for leg in self.legs: res *= leg.customer_odds
        return res
        
    @property
    def liability(self) -> float: return (self.stake * self.total_odds) - self.stake

class RiskDecision(BaseModel):
    ticket_id: str
    action: Literal["REJECT", "ACCEPT_B_BOOK", "ACCEPT_A_BOOK_HEDGE", "ACCEPT_PARTIAL_HEDGE"]
    reason: str
    house_ev: float
    true_probability: float
    hedge_stake: float = 0.0
    hedge_odds: float = 0.0
    b_book_stake: float = 0.0
    
    # 🌟 账本持久化溯源字段
    retained_stake: float = 0.0
    retained_liability: float = 0.0
    danger_match_id: str = ""
    danger_selection: str = ""