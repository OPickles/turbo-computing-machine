from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PINNACLE_API_KEY: str = "your_dev_key"
    REQUEST_TIMEOUT: int = 15
    TEAM_MAPPING_PATH: str = "data/team_mapping.json"
    
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

settings = Settings()