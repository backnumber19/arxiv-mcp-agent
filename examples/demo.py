"""
Demo script for MCP Client with arXiv server

This demonstrates all 3 MCP client primitives:
1. Roots - Filesystem boundaries
2. Sampling - LLM output requests  
3. Elicitation - User input requests
"""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.client.agent import MCPAgent
from src.client.client import MCPClient

load_dotenv()

server_path = os.getenv(
    "ARXIV_SERVER_PATH", "/path/to/arxiv_server"
)

download_path = os.getenv("DOWNLOAD_PATH", os.path.join(os.getcwd(), "downloads"))
ssl_verify = os.getenv("SSL_VERIFY", "false")
SERVER_COMMAND = "python"
SERVER_ARGS = [
    os.path.join(server_path, "server.py")
]

SERVER_ENV = {
    "DOWNLOAD_PATH": download_path,
    "PYTHONPATH": server_path,
    "SSL_VERIFY": ssl_verify,
}

ROOTS = [
    {
        "uri": f"file://{os.getcwd()}",
        "name": "Current Project Directory",
    },
    {
        "uri": f"file://{download_path}",
        "name": "Downloads Directory",
    },
]


async def demo_roots(client: MCPClient):
    print("\n" + "=" * 80)
    print("ROOTS PRIMITIVE DEMO")
    print("=" * 80)
    print("\n1. Roots define filesystem boundaries that the server can access")
    print(f"   Configured roots: {[r['name'] for r in ROOTS]}")
    
    print("\n   Testing Roots callback (simulating server request):")
    roots_result = await client._list_roots_callback()
    for i, root in enumerate(roots_result, 1):
        print(f"      {i}. {root.name}: {root.uri}")
    print("   Roots callback working correctly!")


async def demo_sampling(client: MCPClient):
    """Demonstrate Sampling primitive - 실제 콜백 호출"""
    print("\n" + "=" * 80)
    print("SAMPLING PRIMITIVE DEMO")
    print("=" * 80)
    print("\n2. Sampling allows server to request LLM output")
    print("   When server requests sampling, client uses Bedrock LLM to generate response")
    
    print("\n   Testing Sampling callback (simulating server request):")
    print("   Enter a prompt for the LLM (or press Enter for default):")
    user_prompt = input("   Your prompt: ").strip()
    if not user_prompt:
        user_prompt = "What is machine learning? Give a brief answer."
        print(f"   Using default prompt: {user_prompt}")
    else:
        print(f"   Using your prompt: {user_prompt}")
    
    try:
        from mcp import types
        from mcp.shared.context import RequestContext
        
        params = types.CreateMessageRequestParams(
            messages=[
                types.SamplingMessage(
                    role="user",
                    content=types.TextContent(type="text", text=user_prompt)
                )
            ],
            maxTokens=512
        )
        
        sampling_result = await client._sampling_callback(None, params)
        print(f"\n   LLM Response:")
        if isinstance(sampling_result.content, types.TextContent):
            print(f"   {sampling_result.content.text}")
        elif isinstance(sampling_result.content, list) and sampling_result.content:
            content = sampling_result.content[0]
            if isinstance(content, types.TextContent):
                print(f"   {content.text}")
            else:
                print(f"   {content}")
        else:
            print(f"   {sampling_result.content}")
        print("\n   Sampling callback working correctly!")
    except Exception as e:
        print(f"\n   Sampling error (Bedrock may not be configured): {e}")
        import traceback
        traceback.print_exc()


async def demo_search_arxiv(agent: MCPAgent):
    """Demo: Search arXiv papers"""
    print("\n" + "=" * 80)
    print("ARXIV SEARCH DEMO")
    print("=" * 80)

    print("\nSearch options:")
    print("1. Search by general keyword (all_fields)")
    print("2. Search by title")
    print("3. Search by author")
    print("4. Search by abstract")

    choice = input("\nSelect option (1-4): ").strip()

    if choice == "1":
        query = input("Enter keyword: ").strip()
        if query:
            results = await agent.search_arxiv(all_fields=query)
        else:
            results = await agent.search_arxiv(all_fields="machine learning")
    elif choice == "2":
        query = input("Enter title keyword: ").strip()
        if query:
            results = await agent.search_arxiv(title=query)
        else:
            results = await agent.search_arxiv(title="neural networks")
    elif choice == "3":
        query = input("Enter author name: ").strip()
        if query:
            results = await agent.search_arxiv(author=query)
        else:
            results = await agent.search_arxiv(author="Yann LeCun")
    elif choice == "4":
        query = input("Enter abstract keyword: ").strip()
        if query:
            results = await agent.search_arxiv(abstract=query)
        else:
            results = await agent.search_arxiv(abstract="deep learning")
    else:
        results = await agent.search_arxiv(all_fields="machine learning")

    print(f"\nSearch completed")
    if isinstance(results, list):
        print(f"   Found {len(results)} results")
        for i, result in enumerate(results[:3], 1):
            if isinstance(result, dict):
                print(f"\n  {i}. {result.get('title', 'N/A')}")
            else:
                print(f"\n  {i}. {str(result)[:100]}")


async def demo_get_details(agent: MCPAgent):
    """Demo: Get paper details"""
    print("\n" + "=" * 80)
    print("GET PAPER DETAILS DEMO")
    print("=" * 80)

    title = input("\nEnter paper title (or press Enter for default): ").strip()
    if not title:
        title = "Attention Is All You Need"

    print(f"\nGetting details for: {title}")
    result = await agent.get_details(title)
    print(f"\nDetails retrieved:")
    if isinstance(result, dict):
        for key, value in list(result.items())[:5]:
            print(f"   {key}: {str(value)[:80]}")
    else:
        print(f"   {str(result)[:200]}")


async def demo_download_article(agent: MCPAgent):
    """Demo: Download article"""
    print("\n" + "=" * 80)
    print("DOWNLOAD ARTICLE DEMO")
    print("=" * 80)

    title = input("\nEnter paper title to download: ").strip()
    if not title:
        title = "Attention Is All You Need"

    print(f"\nDownloading: {title}")
    result = await agent.download_article(title)
    print(f"\nDownload result:")
    if isinstance(result, dict):
        print(f"   {result}")
    else:
        print(f"   {str(result)[:200]}")


async def main():
    """Main demo function"""
    print("=" * 80)
    print("MCP CLIENT DEMO - arXiv Integration")
    print("=" * 80)
    print("\nThis demo shows all 3 MCP client primitives:")
    print("  1. Roots - Filesystem boundaries")
    print("  2. Sampling - LLM output requests")
    print("  3. Elicitation - User input requests")

    # Check server path
    server_file = Path(server_path) / "server.py"
    if not server_file.exists():
        print(f"\nError: Server file does not exist: {server_file}")
        print("   Please set ARXIV_SERVER_PATH in .env file")
        return

    # Initialize client first (before connecting to server)
    print("\n" + "=" * 80)
    print("INITIALIZING MCP CLIENT")
    print("=" * 80)
    print(f"Server path: {server_path}")
    print(f"Server file: {server_file}")

    client = MCPClient(
        server_command=SERVER_COMMAND,
        server_args=SERVER_ARGS,
        server_env=SERVER_ENV,
        roots=ROOTS,
    )

    # Show primitive demonstrations BEFORE connecting to server
    # This demonstrates that the primitives are implemented in the client
    await demo_roots(client)
    await demo_sampling(client)

    agent = MCPAgent(client)

    try:
        # Initialize agent (this will connect to server)
        await agent.initialize()

        print("\n" + "=" * 80)
        print("AVAILABLE TOOLS")
        print("=" * 80)
        tools = agent.list_available_tools()
        for tool in tools:
            print(f"  - {tool}")

        # Interactive menu
        while True:
            print("\n" + "=" * 80)
            print("MENU")
            print("=" * 80)
            print("1. Search arXiv")
            print("2. Get Paper Details")
            print("3. Download Article")
            print("4. Exit")

            choice = input("\nSelect option (1-4): ").strip()

            if choice == "1":
                await demo_search_arxiv(agent)
            elif choice == "2":
                await demo_get_details(agent)
            elif choice == "3":
                await demo_download_article(agent)
            elif choice == "4":
                break
            else:
                print("Invalid option")

        await agent.close()

    except KeyboardInterrupt:
        print("\n\nExiting...")
        await agent.close()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())