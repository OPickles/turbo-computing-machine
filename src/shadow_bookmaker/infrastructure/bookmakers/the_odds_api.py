from typing import List
from src.shadow_bookmaker.infrastructure.bookmakers.base import BaseBookmaker
from src.shadow_bookmaker.infrastructure.network import AsyncNetworkEngine
from src.shadow_bookmaker.domain.models import OddsDTO
from src.shadow_bookmaker.config import settings

class TheOddsAPIBookmaker(BaseBookmaker):
    def __init__(self, mapper):
        super().__init__(mapper)
        self.network = AsyncNetworkEngine()

    @property
    def name(self) -> str: return "Pinnacle"
    
    async def fetch_odds(self) -> List[OddsDTO]:
        if not settings.ODDS_API_KEY:
            return []
            
        # 🎯 发射指令：抓取全球即将开赛的足球赛事 (soccer_upcoming)，且只盯防平博 (pinnacle)
        url = "https://api.the-odds-api.com/v4/sports/soccer_upcoming/odds"
        params = {
            "apiKey": settings.ODDS_API_KEY,
            "regions": "eu",
            "markets": "h2h", 
            "bookmakers": "pinnacle"
        }
        
        try:
            data = await self.network.fetch_json(url, params=params)
        except Exception as e:
            print(f"📡 API 抓取拦截 (请检查网络或余额): {e}")
            return []

        results = []
        for match in data:
            home_raw = match.get("home_team", "")
            away_raw = match.get("away_team", "")
            if not home_raw or not away_raw: continue
            
            # 利用你的映射字典做双保险清洗
            home_team = self.mapper.standardize(home_raw)
            away_team = self.mapper.standardize(away_raw)
            match_id = f"{home_team} vs {away_team}"

            for bookie in match.get("bookmakers", []):
                if bookie["key"] == "pinnacle":
                    for market in bookie.get("markets", []):
                        if market["key"] == "h2h":
                            h_odds = a_odds = d_odds = 0.0
                            for outcome in market["outcomes"]:
                                if outcome["name"] == home_raw: h_odds = outcome["price"]
                                elif outcome["name"] == away_raw: a_odds = outcome["price"]
                                elif outcome["name"].lower() == "draw": d_odds = outcome["price"]
                                
                            if h_odds > 1.0 and a_odds > 1.0:
                                results.append(OddsDTO(
                                    bookmaker=self.name, match_id=match_id,
                                    home_team=home_team, away_team=away_team,
                                    home_odds=h_odds, away_odds=a_odds, 
                                    draw_odds=d_odds if d_odds > 1.0 else None
                                ))
        return results