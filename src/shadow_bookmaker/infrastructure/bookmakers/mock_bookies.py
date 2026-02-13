import asyncio
from typing import List
from src.shadow_bookmaker.infrastructure.bookmakers.base import BaseBookmaker
from src.shadow_bookmaker.domain.models import OddsDTO

class PinnacleMock(BaseBookmaker):
    @property
    def name(self) -> str: return "Pinnacle"
    async def fetch_odds(self) -> List[OddsDTO]:
        await asyncio.sleep(0.5)
        # 故意传入脏名字 "Man Utd" 触发 mapper 清洗
        return [OddsDTO(bookmaker=self.name, home_team=self.mapper.standardize("Man Utd"), 
                        away_team=self.mapper.standardize("Spurs"), home_odds=2.10, away_odds=1.85)]

class ScraperMock(BaseBookmaker):
    @property
    def name(self) -> str: return "WildScraper"
    async def fetch_odds(self) -> List[OddsDTO]:
        await asyncio.sleep(0.8)
        # 制造套利空间：客胜赔率给到 2.15 (与平博的 2.10 形成套利)
        return [OddsDTO(bookmaker=self.name, home_team=self.mapper.standardize("Manchester United"), 
                        away_team=self.mapper.standardize("Tottenham Hotspur"), home_odds=1.90, away_odds=2.15)]