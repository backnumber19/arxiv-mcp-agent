"""
MCP Client implementation with all 3 client primitives:
1. Roots - Filesystem boundaries
2. Sampling - LLM output requests
3. Elicitation - User input requests
"""
import asyncio
import os
from typing import Any, Dict, List, Optional

import boto3
from dotenv import load_dotenv
from langchain_aws import ChatBedrock
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.shared.context import RequestContext

load_dotenv()


class MCPClient:
    def __init__(
        self,
        server_command: str,
        server_args: List[str],
        server_env: Optional[Dict[str, str]] = None,
        bedrock_config: Optional[Dict[str, str]] = None,
        roots: Optional[List[Dict[str, str]]] = None,
    ):
        self.server_params = StdioServerParameters(
            command=server_command,
            args=server_args,
            env=server_env or {},
        )
        self.session: Optional[ClientSession] = None
        self._read = None
        self._write = None
        self._stdio_context = None
        self._session_context = None
        self._connected = False

        # Bedrock LLM for Sampling primitive
        bedrock_config = bedrock_config or {
            "region": os.getenv("AWS_REGION", "us-west-2"),
            "model_id": os.getenv(
                "BEDROCK_MODEL", "anthropic.claude-3-haiku-20240307-v1:0"
            ),
        }
        self.llm = ChatBedrock(
            client=boto3.client(
                "bedrock-runtime", region_name=bedrock_config["region"]
            ),
            model_id=bedrock_config["model_id"],
            model_kwargs={"temperature": 0.1, "max_tokens": 512},
        )

        # Roots primitive: filesystem boundaries
        self.roots = roots or [
            {
                "uri": f"file://{os.getcwd()}",
                "name": "Current Working Directory",
            }
        ]

        # Elicitation: pending user input requests
        self.pending_elicitation: Optional[Dict[str, Any]] = None

    async def _list_roots_callback(self) -> List[types.Root]:
        """Callback for Roots primitive - server requests roots list"""
        return [
            types.Root(uri=root["uri"], name=root["name"]) 
            for root in self.roots
        ]

    async def _sampling_callback(
        self,
        context: RequestContext[ClientSession, None],
        params: types.CreateMessageRequestParams
    ) -> types.CreateMessageResult:
        """
        Callback for Sampling primitive - server requests LLM output
        """
        # Extract prompt from messages
        prompt = ""
        if params.messages:
            first_msg = params.messages[0]
            # Message.content는 list[Content] 또는 Content일 수 있음
            if hasattr(first_msg, 'content'):
                if isinstance(first_msg.content, list) and first_msg.content:
                    content = first_msg.content[0]
                    if isinstance(content, types.TextContent):
                        prompt = content.text
                elif isinstance(first_msg.content, types.TextContent):
                    prompt = first_msg.content.text
        
        if not prompt:
            prompt = ""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            
            return types.CreateMessageResult(
                role="assistant",
                content=types.TextContent(type="text", text=content),
                model="claude",
                stopReason="endTurn",
            )
        except Exception as e:
            return types.CreateMessageResult(
                role="assistant",
                content=types.TextContent(type="text", text=f"Error: {str(e)}"),
                model="claude",
                stopReason="stop",
            )

    async def _elicitation_callback(self, params: Dict[str, Any]) -> str:
        """
        Callback for Elicitation primitive - server requests user input
        
        Note: Using simple Dict-based signature for compatibility with demo.py
        MCP specification: https://modelcontextprotocol.io/specification/2025-06-18/client/elicitation
        """
        prompt = params.get("prompt", "")
        request_id = params.get("request_id")

        if not prompt:
            return ""

        self.pending_elicitation = {
            "request_id": request_id,
            "prompt": prompt,
            "params": params,
        }

        print(f"Elicitation request: {prompt}")
        return ""

    async def connect(self):
        """Connect to MCP server"""
        self._stdio_context = stdio_client(self.server_params)
        self._read, self._write = await self._stdio_context.__aenter__()
        
        self._session_context = ClientSession(
            self._read,
            self._write,
            sampling_callback=self._sampling_callback,
            list_roots_callback=self._list_roots_callback,
            elicitation_callback=self._elicitation_callback,
        )
        self.session = await self._session_context.__aenter__()

        init_result = await self.session.initialize()
        self._connected = True
        print(f"✅ Connected to MCP server: {init_result.serverInfo.name}")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from server"""
        if not self.session:
            return []

        try:
            result = await self.session.list_tools()
            return [{"name": tool.name, "description": tool.description} for tool in result.tools]
        except Exception as e:
            print(f"❌ Error listing tools: {e}")
            return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the server"""
        if not self.session:
            return {"error": "Not connected"}

        try:
            result = await self.session.call_tool(name, arguments)
            
            if result.content:
                first_content = result.content[0]
                
                if hasattr(first_content, "text"):
                    text_result = first_content.text
                    
                    if isinstance(text_result, str):
                        if text_result.strip().startswith(("{", "[")):
                            import json
                            try:
                                return json.loads(text_result)
                            except json.JSONDecodeError:
                                pass
                        return text_result
                    return text_result
                elif hasattr(first_content, "data"):
                    return first_content.data
                else:
                    return str(first_content)
            
            if hasattr(result, "structuredContent") and result.structuredContent:
                return result.structuredContent
            
            return {"result": "No content returned"}
        except Exception as e:
            print(f"❌ Error calling tool {name}: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources from server"""
        if not self.session:
            return []

        try:
            result = await self.session.list_resources()
            return [{"uri": r.uri, "name": r.name, "mimeType": r.mimeType} for r in result.resources]
        except Exception as e:
            print(f"❌ Error listing resources: {e}")
            return []

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from server"""
        if not self.session:
            return {"error": "Not connected"}

        try:
            result = await self.session.read_resource(uri)
            contents = []
            for content in result.contents:
                if hasattr(content, "text"):
                    contents.append({"type": "text", "text": content.text})
                elif hasattr(content, "data"):
                    contents.append({"type": "blob", "data": content.data})
            return {"contents": contents}
        except Exception as e:
            return {"error": str(e)}

    def get_pending_elicitation(self) -> Optional[Dict[str, Any]]:
        """Get pending elicitation request"""
        return self.pending_elicitation

    async def respond_elicitation(
        self, response: str, request_id: Optional[str] = None
    ):
        """Respond to elicitation request"""
        if not self.session:
            return

        request_id = request_id or (
            self.pending_elicitation.get("request_id")
            if self.pending_elicitation
            else None
        )

        if not request_id:
            print("❌ No pending elicitation request")
            return

        try:
            await self.session.send_notification(
                "elicitation/response",
                {
                    "request_id": request_id,
                    "response": response,
                },
            )
            self.pending_elicitation = None
            print(f"✅ Elicitation response sent: {response}")
        except Exception as e:
            print(f"❌ Error responding to elicitation: {e}")

    async def close(self):
        """Close connection to server"""
        if self.session and self._session_context:
            try:
                await self._session_context.__aexit__(None, None, None)
            except Exception:
                pass
            self.session = None
            self._session_context = None
        
        if self._stdio_context:
            try:
                await self._stdio_context.__aexit__(None, None, None)
            except Exception:
                pass
            self._stdio_context = None
        
        self._read = None
        self._write = None
        self._connected = False
        print("✅ MCP connection closed")