import aiohttp
from typing import Dict, Any

class PrometheusAdapter:
    def __init__(self, base_url: str = "http://prometheus-operated.monitoring.svc.cluster.local:9090"):
        self.base_url = base_url

    async def query(self, query: str) -> Dict[str, Any]:
        """Runs an instant query against Prometheus."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/v1/query", params={"query": query}) as response:
                response.raise_for_status()
                return await response.json()

    async def query_range(self, query: str, start: str, end: str, step: str) -> Dict[str, Any]:
        """Runs a range query over a given time duration."""
        params = {
            "query": query,
            "start": start,
            "end": end,
            "step": step
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/v1/query_range", params=params) as response:
                response.raise_for_status()
                return await response.json()

prometheus_client = PrometheusAdapter()
