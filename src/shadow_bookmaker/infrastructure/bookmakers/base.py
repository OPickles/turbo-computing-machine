from abc import ABC, abstractmethod
from typing import List
from src.shadow_bookmaker.domain.models import OddsDTO

class BaseBookmaker(ABC):
    def __init__(self, mapper): self.mapper = mapper
    @property
    @abstractmethod
    def name(self) -> str: pass
    @abstractmethod
    async def fetch_odds(self) -> List[OddsDTO]: pass