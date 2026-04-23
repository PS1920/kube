import aiohttp
from typing import Dict, Any

class LokiAdapter:
    def __init__(self, base_url: str = "http://loki.monitoring.svc.cluster.local:3100"):
        self.base_url = base_url

    async def query_range(self, query: str, start: str, end: str, limit: int = 100) -> Dict[str, Any]:
        """Runs a range log query against Loki."""
        params = {
            "query": query,
            "start": start,
            "end": end,
            "limit": limit
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/loki/api/v1/query_range", params=params) as response:
                response.raise_for_status()
                return await response.json()

loki_client = LokiAdapter()
