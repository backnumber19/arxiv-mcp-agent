import asyncio
from typing import Dict, List, Optional

from src.client.client import MCPClient


class MCPAgent:
    def __init__(self, client: MCPClient):
        self.client = client
        self.tools_cache: List[Dict] = []
        self.resources_cache: List[Dict] = []

    async def initialize(self):
        await self.client.connect()

        self.tools_cache = await self.client.list_tools()
        print(f"Loaded {len(self.tools_cache)} tools")

        self.resources_cache = await self.client.list_resources()
        print(f"Loaded {len(self.resources_cache)} resources")

    async def search_arxiv(
        self,
        all_fields: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        abstract: Optional[str] = None,
        start: int = 0,
    ) -> List[Dict]:
        params = {}
        if all_fields:
            params["all_fields"] = all_fields
        if title:
            params["title"] = title
        if author:
            params["author"] = author
        if abstract:
            params["abstract"] = abstract
        if start:
            params["start"] = start

        result = await self.client.call_tool("search_arxiv", params)
        
        if isinstance(result, dict):
            if "error" in result:
                return [result]
            if result and all(isinstance(k, str) and isinstance(v, dict) for k, v in list(result.items())[:3]):
                return [{"title": title, **details} for title, details in result.items()]
            return [result]
        elif isinstance(result, list):
            return result
        elif isinstance(result, str):
            if "Unable to retrieve" in result or "error" in result.lower():
                return [{"error": result}]
            import json
            try:
                parsed = json.loads(result)
                if isinstance(parsed, dict):
                    if all(isinstance(k, str) and isinstance(v, dict) for k, v in parsed.items()):
                        return [{"title": title, **details} for title, details in parsed.items()]
                return parsed if isinstance(parsed, list) else [parsed]
            except json.JSONDecodeError:
                return [{"error": result}]
        else:
            return [result] if result else []

    async def get_details(self, title: str) -> Dict:
        result = await self.client.call_tool("get_details", {"title": title})
        return result

    async def get_article_url(self, title: str) -> Dict:
        result = await self.client.call_tool("get_article_url", {"title": title})
        return result

    async def download_article(self, title: str) -> Dict:
        result = await self.client.call_tool("download_article", {"title": title})
        return result

    async def load_article_to_context(self, title: str) -> Dict:
        result = await self.client.call_tool("load_article_to_context", {"title": title})
        return result

    def list_available_tools(self) -> List[str]:
        return [tool.get("name", "") for tool in self.tools_cache if tool.get("name")]

    async def close(self):
        await self.client.close()