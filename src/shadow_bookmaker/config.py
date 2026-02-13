from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ODDS_API_KEY: str = ""  # 🌟 真实外盘的上帝之钥
    REQUEST_TIMEOUT: int = 15
    TEAM_MAPPING_PATH: str = "data/team_mapping.json"
    
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

settings = Settings()