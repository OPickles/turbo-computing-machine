import asyncio
from typing import List
from src.shadow_bookmaker.infrastructure.bookmakers.base import BaseBookmaker
from src.shadow_bookmaker.domain.models import OddsDTO

class PinnacleMock(BaseBookmaker):
    @property
    def name(self) -> str: return "Pinnacle"
    
    async def fetch_odds(self) -> List[OddsDTO]:
        await asyncio.sleep(0.5)
        return [
            # 赛事 1：曼联 vs 热刺
            OddsDTO(
                bookmaker=self.name, 
                match_id="Manchester United vs Tottenham Hotspur", # 🎯 修复：补齐必填指纹
                home_team=self.mapper.standardize("Man Utd"), 
                away_team=self.mapper.standardize("Spurs"), 
                home_odds=2.10, 
                away_odds=3.20,
                draw_odds=3.50 # 🎯 修复：补齐平局，让去水算法完美闭环
            ),
            # 赛事 2：皇马 vs 巴萨 (专为接下来的“二串一”准备)
            OddsDTO(
                bookmaker=self.name, 
                match_id="Real Madrid vs Barcelona", 
                home_team="Real Madrid", 
                away_team="Barcelona", 
                home_odds=1.80, 
                away_odds=4.20,
                draw_odds=3.80
            )
        ]

class ScraperMock(BaseBookmaker):
    @property
    def name(self) -> str: return "WildScraper"
    async def fetch_odds(self) -> List[OddsDTO]:
        return [] # 作为做市商，初期有 Pinnacle 大盘当风控锚点就够了，暂时放空野鸡爬虫