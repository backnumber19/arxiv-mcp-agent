import asyncio
import json
import re
from typing import Any, Dict, List

from src.client.client import MCPClient


class MCPAgent:
    def __init__(self, client: MCPClient):
        self.client = client
        self.tools_cache: List[Dict] = []
        self.resources_cache: List[Dict] = []

    def _format_tools_for_llm(self) -> str:
        tools_desc = []
        for tool in self.tools_cache:
            tools_desc.append(
                f"""
Tool: {tool['name']}
Description: {tool['description']}
"""
            )
        return "\n".join(tools_desc)

    def _extract_json_from_response(self, text: str) -> Dict:
        """Extract JSON from LLM response (handles markdown code blocks, etc.)"""
        if not text or not text.strip():
            raise ValueError("Empty response from LLM")

        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError as e:
                print(f"JSON parse error in code block: {e}")

        json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError as e:
                print(f"JSON parse error in direct match: {e}")

        raise ValueError(
            f"Could not extract JSON from LLM response. Response: {text[:500]}"
        )

    async def _llm_select_tool(self, user_query: str, tools_description: str) -> Dict:
        """LLM selects appropriate tool and parameters"""
        prompt = f"""You are a tool selection assistant. Based on the user's request, determine which tool to use.

User request: {user_query}

Available tools:
{tools_description}

IMPORTANT: You MUST respond with ONLY a valid JSON object in this exact format:
{{
    "tool_name": "tool_name_here",
    "arguments": {{"param1": "value1", "param2": "value2"}}
}}

Do not include any additional text, explanations, or markdown formatting. Only the JSON object.
"""
        try:
            response = self.client.llm.invoke(prompt)

            if hasattr(response, "content"):
                content = response.content
            elif isinstance(response, str):
                content = response
            else:
                content = str(response)

            if not content or not content.strip():
                raise ValueError("Empty response from LLM")

            tool_selection = self._extract_json_from_response(content)

            if "tool_name" not in tool_selection:
                raise ValueError("Invalid tool selection: missing 'tool_name' field")
            if "arguments" not in tool_selection:
                tool_selection["arguments"] = {}

            tool_names = [t.get("name") for t in self.tools_cache]
            if tool_selection["tool_name"] not in tool_names:
                print(
                    f"Warning: Tool '{tool_selection['tool_name']}' not found. Available: {tool_names}"
                )
                if "search_arxiv" in tool_names:
                    tool_selection["tool_name"] = "search_arxiv"
                elif tool_names:
                    tool_selection["tool_name"] = tool_names[0]

            return tool_selection

        except Exception as e:
            print(f"Error selecting tool: {e}")
            print(f"   User query: {user_query}")

            tool_names = [t.get("name") for t in self.tools_cache]
            if "search_arxiv" in tool_names:
                return {
                    "tool_name": "search_arxiv",
                    "arguments": {"all_fields": user_query},
                }
            elif tool_names:
                return {"tool_name": tool_names[0], "arguments": {}}
            else:
                raise Exception(f"No tools available and LLM selection failed: {e}")

    async def _llm_explain_result(self, user_query: str, result: Any) -> str:
        """LLM explains tool results in natural language"""
        prompt = f"""
User request: {user_query}
Tool execution result: {result}

Explain the result in a friendly manner to the user.
"""
        try:
            response = self.client.llm.invoke(prompt)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            print(f"Error explaining result: {e}")
            return f"Tool executed successfully. Result: {str(result)[:200]}"

    async def process_user_request(self, user_query: str) -> str:
        """
        Main entry point: LLM automatically selects tool and explains results

        Args:
            user_query: Natural language request from user

        Returns:
            Natural language explanation of results
        """
        try:
            # 1. Format available tools for LLM
            tools_description = self._format_tools_for_llm()

            # 2. LLM selects tool and parameters
            tool_selection = await self._llm_select_tool(user_query, tools_description)
            print(f"✅ Selected tool: {tool_selection['tool_name']}")
            print(f"   Arguments: {tool_selection['arguments']}")

            # 3. Execute selected tool (MCP communication)
            result = await self.client.call_tool(
                tool_selection["tool_name"], tool_selection["arguments"]
            )

            # 4. LLM explains results
            explanation = await self._llm_explain_result(user_query, result)

            return explanation
        except Exception as e:
            print(f"Error processing request: {e}")
            import traceback

            traceback.print_exc()
            return f"Error processing request: {str(e)}"

    async def initialize(self):
        """Initialize connection and cache tools/resources"""
        await self.client.connect()

        self.tools_cache = await self.client.list_tools()
        print(f"Loaded {len(self.tools_cache)} tools")

        self.resources_cache = await self.client.list_resources()
        print(f"Loaded {len(self.resources_cache)} resources")

    def list_available_tools(self) -> List[str]:
        """List available tool names"""
        return [tool.get("name", "") for tool in self.tools_cache if tool.get("name")]

    async def close(self):
        """Close connection to server"""
        await self.client.close()
