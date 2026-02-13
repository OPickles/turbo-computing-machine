import asyncio
from typing import List
from collections import defaultdict
from src.shadow_bookmaker.application.team_mapper import TeamMapper
from src.shadow_bookmaker.domain.calculator import ArbitrageCalculator
from src.shadow_bookmaker.domain.models import ArbitrageOpportunity
from src.shadow_bookmaker.infrastructure.bookmakers.mock_bookies import PinnacleMock, ScraperMock

class ArbitrageOrchestrator:
    def __init__(self):
        self.mapper = TeamMapper()
        self.calculator = ArbitrageCalculator()
        # 依赖注入：这里你随时可以增加/替换为真实的 API 和爬虫
        self.bookmakers = [PinnacleMock(self.mapper), ScraperMock(self.mapper)]

    async def run_scan(self) -> List[ArbitrageOpportunity]:
        # 1. 【高并发】无视阻塞，同时向所有盘口开火抓取
        tasks = [bookie.fetch_odds() for bookie in self.bookmakers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 2. 【数据对齐】按洗干净的比赛实体放进同一个桶里
        match_pool = defaultdict(list)
        for res in results:
            if isinstance(res, Exception): continue
            for odds in res:
                teams = sorted([odds.home_team, odds.away_team])
                odds.match_id = f"{teams[0]} vs {teams[1]}"
                match_pool[odds.match_id].append(odds)

        # 3. 【数学结算】找套利
        opportunities = []
        for match_id, odds_list in match_pool.items():
            opp = self.calculator.calculate_2way(odds_list)
            if opp: opportunities.append(opp)
                    
        return sorted(opportunities, key=lambda x: x.profit_margin, reverse=True)