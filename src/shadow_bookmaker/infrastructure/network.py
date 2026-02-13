import httpx
from tenacity import retry, wait_exponential, stop_after_attempt
from src.shadow_bookmaker.config import settings

class AsyncNetworkEngine:
    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    # ⚡ 增加 params 参数支持，用于把 API Key 传给外网
    async def fetch_json(self, url: str, headers: dict = None, params: dict = None) -> dict:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()