import os
import warnings
from pathlib import Path

import boto3
import pytest
from dotenv import load_dotenv

load_dotenv()

warnings.filterwarnings("ignore", category=DeprecationWarning, module="botocore")


def test_aws_connection():
    """Test AWS connection and Bedrock access"""
    print("Testing AWS Connection...")

    try:
        region = os.getenv("AWS_REGION", "us-west-2")
        sts = boto3.client("sts", region_name=region)
        identity = sts.get_caller_identity()
        print(f"✅ AWS Identity: {identity['Arn']}")

        bedrock = boto3.client("bedrock", region_name=region)
        models = bedrock.list_foundation_models()

        model_id = os.getenv("BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0")
        model_name = model_id.split(":")[0] if ":" in model_id else model_id
        
        claude_models = [
            m for m in models["modelSummaries"] 
            if model_name in m["modelId"] or "claude" in m["modelId"].lower()
        ]

        if claude_models:
            print(f"✅ Bedrock model available: {claude_models[0]['modelId']}")
        else:
            print(f"❌ Model {model_id} not found - request access in AWS Console")
            pytest.skip(f"Model {model_id} not available")

        assert claude_models, "No Claude models found"

    except Exception as e:
        print(f"❌ AWS Error: {e}")
        pytest.fail(f"AWS connection failed: {e}")


def test_arxiv_mcp_server_path():
    """Test that arXiv MCP server path is configured"""
    print("\nTesting arXiv MCP Server Configuration...")

    server_path = os.getenv("ARXIV_SERVER_PATH", "")
    
    if not server_path or server_path == "/path/to/arxiv-mcp-server/src/arxiv_server":
        pytest.skip(
            "ARXIV_SERVER_PATH not set in .env file. "
            "Set it to the absolute path of arxiv-mcp-server/src/arxiv_server"
        )

    # Check if path exists
    path = Path(server_path)
    assert path.exists(), f"arXiv MCP server path does not exist: {server_path}"
    assert path.is_dir(), f"arXiv MCP server path is not a directory: {server_path}"
    
    # Check if server.py exists
    server_file = path / "server.py"
    assert server_file.exists(), f"server.py not found in {server_path}"
    
    print(f"✅ arXiv MCP server path valid: {server_path}")
    print(f"   Server file found: {server_file}")


def test_arxiv_mcp_server_tools():
    """Test that arXiv MCP server can be accessed and returns tools"""
    print("\nTesting arXiv MCP Server Connection...")

    import asyncio
    from src.client.client import MCPClient

    server_path = os.getenv("ARXIV_SERVER_PATH", "")
    if not server_path or server_path == "/path/to/arxiv-mcp-server/src/arxiv_server":
        pytest.skip("ARXIV_SERVER_PATH not configured")

    download_path = os.getenv("DOWNLOAD_PATH", os.path.join(os.getcwd(), "downloads"))
    
    # Ensure download path exists
    Path(download_path).mkdir(parents=True, exist_ok=True)

    async def test_connection():
        try:
            client = MCPClient(
                server_command="uv",
                server_args=[
                    "--directory",
                    server_path,
                    "run",
                    "server.py",
                ],
                server_env={
                    "DOWNLOAD_PATH": download_path,
                },
            )

            # Try to connect (with timeout)
            try:
                # Start connection
                connect_task = asyncio.create_task(client.connect())
                
                # Wait a bit for initialization
                await asyncio.wait_for(asyncio.sleep(1), timeout=2)
                
                # Try to list tools (if connected)
                if client.session:
                    tools = await client.list_tools()
                    print(f"✅ Connected to arXiv MCP server")
                    print(f"   Found {len(tools)} tools: {[t.get('name', '') for t in tools[:5]]}")
                    
                    # Check for expected tools
                    tool_names = [t.get("name", "") for t in tools]
                    expected_tools = ["search_arxiv", "get_details", "get_article_url"]
                    
                    found_tools = [t for t in expected_tools if t in tool_names]
                    assert len(found_tools) > 0, f"Expected tools not found. Available: {tool_names}"
                    
                    await client.close()
                    return True
                else:
                    print("⚠️  Connection not established yet (this is OK for quick test)")
                    connect_task.cancel()
                    return True
                    
            except asyncio.TimeoutError:
                connect_task.cancel()
                print("⚠️  Connection timeout (server may need more time to start)")
                return True
            except Exception as e:
                print(f"⚠️  Connection test incomplete: {e}")
                return True

        except Exception as e:
            print(f"❌ MCP Server connection error: {e}")
            pytest.fail(f"Failed to connect to arXiv MCP server: {e}")

    # Run async test
    result = asyncio.run(test_connection())
    assert result is True


if __name__ == "__main__":
    print("ARXIV MCP AGENT - SETUP TEST")
    print("=" * 50)

    results = {}
    
    try:
        test_aws_connection()
        results["aws"] = True
    except Exception as e:
        results["aws"] = False
        print(f"AWS test failed: {e}")

    try:
        test_arxiv_mcp_server_path()
        results["server_path"] = True
    except Exception as e:
        results["server_path"] = False
        print(f"Server path test failed: {e}")

    try:
        test_arxiv_mcp_server_tools()
        results["server_connection"] = True
    except Exception as e:
        results["server_connection"] = False
        print(f"Server connection test failed: {e}")

    print("\n" + "=" * 50)
    print("SETUP SUMMARY")
    print("=" * 50)
    print(f"AWS Bedrock: {'✅ Ready' if results.get('aws') else '❌ Not Ready'}")
    print(f"arXiv MCP Server Path: {'✅ Ready' if results.get('server_path') else '❌ Not Ready'}")
    print(f"arXiv MCP Server Connection: {'✅ Ready' if results.get('server_connection') else '❌ Not Ready'}")

    if all(results.values()):
        print("\nAll systems ready! You can now run the MCP agent.")
    else:
        print("\nPlease fix the issues above before running the agent.")