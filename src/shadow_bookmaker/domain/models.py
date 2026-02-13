from pydantic import BaseModel, Field
from typing import Optional, Dict

class OddsDTO(BaseModel):
    bookmaker: str
    match_id: str = ""
    home_team: str
    away_team: str
    home_odds: float = Field(gt=1.0)
    away_odds: float = Field(gt=1.0)
    draw_odds: Optional[float] = None

class ArbitrageOpportunity(BaseModel):
    match_id: str
    profit_margin: float
    best_home_odds: float
    best_home_bookie: str
    best_away_odds: float
    best_away_bookie: str
    recommended_stakes: Dict[str, float]
    total_investment: float