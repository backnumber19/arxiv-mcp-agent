import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.client.agent import MCPAgent
from src.client.client import MCPClient

load_dotenv()

server_path = os.getenv("ARXIV_SERVER_PATH", "/path/to/arxiv_server")

download_path = os.getenv("DOWNLOAD_PATH", os.path.join(os.getcwd(), "downloads"))
ssl_verify = os.getenv("SSL_VERIFY", "false")
SERVER_COMMAND = "python"
SERVER_ARGS = [os.path.join(server_path, "server.py")]

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


async def demo_search_arxiv(agent: MCPAgent):
    print("\n" + "=" * 80)
    print("ARXIV SEARCH DEMO (LLM-based)")
    print("=" * 80)

    print("\nEnter your search request:")
    user_query = input("   Your query: ").strip()
    if not user_query:
        user_query = "Find papers about machine learning"
        print(f"   Using default: {user_query}")

    print(f"\nProcessing request: {user_query}")
    explanation = await agent.process_user_request(user_query)

    print(f"\nResult:")
    print(f"   {explanation}")


async def demo_get_details(agent: MCPAgent):
    print("\n" + "=" * 80)
    print("GET PAPER DETAILS DEMO (LLM-based)")
    print("=" * 80)

    title = input("\nEnter paper title (or press Enter for default): ").strip()
    if not title:
        title = "Attention Is All You Need"

    user_query = f"Get details for the paper: {title}"
    print(f"\nProcessing request: {user_query}")

    explanation = await agent.process_user_request(user_query)

    print(f"\nResult:")
    print(f"   {explanation}")


async def demo_download_article(agent: MCPAgent):
    print("\n" + "=" * 80)
    print("DOWNLOAD ARTICLE DEMO (LLM-based)")
    print("=" * 80)

    title = input("\nEnter paper title to download: ").strip()
    if not title:
        title = "Attention Is All You Need"

    user_query = f"Download the paper: {title}"
    print(f"\nProcessing request: {user_query}")

    explanation = await agent.process_user_request(user_query)

    print(f"\nResult:")
    print(f"   {explanation}")


async def main():
    print("=" * 80)
    print("MCP CLIENT DEMO - arXiv Integration")
    print("=" * 80)
    print("\nThis demo shows:")
    print("  1. Roots - Filesystem boundaries")
    print("  2. Sampling - LLM output requests")
    print("  3. LLM-based tool selection - Automatic tool selection and execution")

    server_file = Path(server_path) / "server.py"
    if not server_file.exists():
        print(f"\nError: Server file does not exist: {server_file}")
        print("   Please set ARXIV_SERVER_PATH in .env file")
        return

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
    await demo_roots(client)
    agent = MCPAgent(client)

    try:
        await agent.initialize()

        print("\n" + "=" * 80)
        print("AVAILABLE TOOLS")
        print("=" * 80)
        tools = agent.list_available_tools()
        for tool in tools:
            print(f"  - {tool}")

        while True:
            print("\n" + "=" * 80)
            print("MENU")
            print("=" * 80)
            print("1. Custom Request (LLM-based)")
            print("2. Exit")

            choice = input("\nSelect option (1-2): ").strip()

            if choice == "1":
                user_query = input("\nEnter your request: ").strip()
                if user_query:
                    print(f"\nProcessing request: {user_query}")
                    explanation = await agent.process_user_request(user_query)
                    print(f"\nResult:")
                    print(f"   {explanation}")
            elif choice == "2":
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
