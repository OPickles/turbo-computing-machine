import json
import os
from thefuzz import process
from src.shadow_bookmaker.config import settings

class TeamMapper:
    """防腐层：把万国牌名字洗成标准拼写"""
    def __init__(self):
        self.mapping = {}
        if os.path.exists(settings.TEAM_MAPPING_PATH):
            with open(settings.TEAM_MAPPING_PATH, 'r', encoding='utf-8') as f:
                self.mapping = json.load(f)
        self.standard_names = list(set(self.mapping.values())) if self.mapping else []
        
    def standardize(self, raw_name: str) -> str:
        if not raw_name: return "Unknown"
        if raw_name in self.mapping: return self.mapping[raw_name]
        
        if self.standard_names:
            best_match, score = process.extractOne(raw_name, self.standard_names)
            if score >= 85: return best_match # 模糊匹配兜底
            
        return raw_name