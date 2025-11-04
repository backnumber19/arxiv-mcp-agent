# arXiv MCP Agent

[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A complete Model Context Protocol (MCP) implementation featuring both a client and server for interacting with the arXiv API. This project demonstrates all three MCP client primitives (Roots, Sampling, Elicitation) and provides a fully functional arXiv search and download service.

**One of the core strengths of MCP is its reusable server ecosystem** - this project uses the arXiv MCP server from [blazickjp/arxiv-mcp-server](https://github.com/blazickjp/arxiv-mcp-server), demonstrating how MCP clients can seamlessly integrate with existing servers in the ecosystem.

## Features

### MCP Client Primitives
- **Roots**: Filesystem boundaries that define server access permissions
- **Sampling**: LLM output requests using AWS Bedrock
- **Elicitation**: User input requests for interactive operations

### arXiv Server Tools
- **search_arxiv**: Search arXiv database with flexible query options
- **get_details**: Retrieve comprehensive metadata about articles
- **get_article_url**: Get direct URLs to articles
- **download_article**: Download PDF files to local storage
- **load_article_to_context**: Extract text content from PDFs for LLM context

## Project Structure

```
arxiv-mcp-agent/
├── src/
│   ├── client/               # MCP Client implementation
│   │   ├── __init__.py
│   │   ├── client.py         # MCPClient with all 3 primitives
│   │   └── agent.py          # High-level agent wrapper
│   └── server/               # MCP Server implementation
│       ├── src/
│       │   └── arxiv_server/
│       │       └── server.py # FastMCP server with arXiv tools
│       ├── pyproject.toml
│       └── README.md
├── examples/
│   └── demo.py               # Interactive demo script
├── downloads/                # PDF download directory
├── tests/                    # Test files
├── requirements.txt          
└── README.md                 
```

## Internal Architecture Flow
```mermaid
sequenceDiagram
    participant User
    participant Demo
    participant Agent
    participant Client
    participant Server

    User->>Demo: python demo.py
    Demo->>Client: MCPClient initialization
    Demo->>Client: client.connect()
    Client->>Server: stdio connection established
    
    Demo->>Agent: MCPAgent(client)
    Agent->>Client: client.list_tools()
    Client->>Server: list_tools request
    Server-->>Client: tools list
    
    User->>Demo: Select "Search arXiv"
    Demo->>Agent: agent.search_arxiv("AI")
    Agent->>Client: client.call_tool("search_arxiv")
    Client->>Server: call_tool request
    Server->>Server: arXiv API call
    Server-->>Client: results
    Client-->>Agent: parsed results
    Agent-->>Demo: formatted results
    Demo-->>User: display results
    
    User->>Demo: Exit
    Demo->>Agent: agent.close()
    Agent->>Client: client.close()
    Client->>Server: connection closed
```

## Installation

### Prerequisites
- Python 3.10+
- AWS Account with Bedrock access (for Sampling primitive)
- Virtual environment (recommended)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/backnumber19/arxiv-mcp-agent.git
cd arxiv-mcp-agent
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
AWS_REGION=us-west-2
BEDROCK_MODEL=anthropic.claude-3-haiku-20240307-v1:0
ARXIV_SERVER_PATH=/absolute/path/to/src/server/src/arxiv_server
DOWNLOAD_PATH=/absolute/path/to/downloads
SSL_VERIFY=false
```

## Usage

### Running the Demo

The demo script showcases all three MCP client primitives and provides an interactive interface for arXiv operations:

```bash
python examples/demo.py
```

The demo includes:
1. **Roots Demo**: Demonstrates filesystem boundary configuration
2. **Sampling Demo**: Tests LLM integration with Bedrock
3. **Interactive Menu**: Search, download, and explore arXiv articles

### Using the Client Programmatically

```python
import asyncio
from src.client.agent import MCPAgent
from src.client.client import MCPClient

async def main():
    # Initialize client
    client = MCPClient(
        server_command="python",
        server_args=["/path/to/server.py"],
        server_env={"DOWNLOAD_PATH": "/path/to/downloads"},
        roots=[
            {"uri": "file:///current/dir", "name": "Current Directory"},
            {"uri": "file:///downloads", "name": "Downloads"}
        ]
    )
    
    # Create agent
    agent = MCPAgent(client)
    await agent.initialize()
    
    # Search arXiv
    results = await agent.search_arxiv(all_fields="machine learning")
    
    # Get article details
    details = await agent.get_details("Attention Is All You Need")
    
    # Download article
    download_result = await agent.download_article("Attention Is All You Need")
    
    await agent.close()

asyncio.run(main())
```

### MCP Client Primitives

#### 1. Roots
Defines filesystem boundaries that the server can access:

```python
roots = [
    {"uri": "file:///path/to/allowed/dir", "name": "Allowed Directory"}
]
client = MCPClient(..., roots=roots)
```

#### 2. Sampling
Enables server to request LLM output. Configured with AWS Bedrock:

```python
# Configured via environment variables or bedrock_config parameter
bedrock_config = {
    "region": "us-west-2",
    "model_id": "anthropic.claude-3-haiku-20240307-v1:0"
}
```

#### 3. Elicitation
Allows server to request user input:

```python
# Check for pending requests
pending = client.get_pending_elicitation()
if pending:
    response = input(pending["prompt"])
    await client.respond_elicitation(response, pending["request_id"])
```

## Architecture

### MCPClient (`src/client/client.py`)
Core client implementation with:
- `_list_roots_callback()`: Returns configured filesystem roots
- `_sampling_callback()`: Handles LLM requests via Bedrock
- `_elicitation_callback()`: Manages user input requests
- `connect()`: Establishes stdio connection to server
- `call_tool()`: Invokes server tools
- `list_tools()`: Enumerates available server tools

### MCPAgent (`src/client/agent.py`)
High-level wrapper providing:
- Convenient methods for arXiv operations
- Result parsing and error handling
- Tool caching for performance

### Server (`src/server/src/arxiv_server/server.py`)

The arXiv server implementation is based on [blazickjp/arxiv-mcp-server](https://github.com/blazickjp/arxiv-mcp-server/tree/main/src/arxiv_mcp_server). This exemplifies MCP's core philosophy: **clients can leverage any MCP-compatible server from the ecosystem**, enabling rapid development and interoperability.

The server is a FastMCP-based implementation providing:
- arXiv API integration via httpx
- PDF processing with PyMuPDF
- Fuzzy title matching for article lookup
- Error handling and validation

**Note**: The server code in `src/server/` is cloned from the upstream repository. This demonstrates how MCP clients can integrate with existing servers without modification, showcasing the protocol's composability and ecosystem approach.


## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region for Bedrock | `us-west-2` |
| `BEDROCK_MODEL` | Bedrock model ID | `anthropic.claude-3-haiku-20240307-v1:0` |
| `ARXIV_SERVER_PATH` | Path to server directory | Required |
| `DOWNLOAD_PATH` | PDF download directory | `./downloads` |
| `SSL_VERIFY` | Enable SSL verification | `false` |

### Roots Configuration

Roots define filesystem boundaries for security:

```python
ROOTS = [
    {
        "uri": "file:///absolute/path/to/allowed/dir",
        "name": "Human-readable name"
    }
]
```

## Dependencies

### Core
- `mcp==1.20.0` - Model Context Protocol SDK
- `fastmcp==2.13.0.2` - FastMCP server framework
- `pydantic==2.12.3` - Data validation

### AWS Integration
- `boto3==1.35.91` - AWS SDK
- `langchain-aws==0.2.9` - LangChain AWS integration

### arXiv Integration
- `httpx==0.28.1` - Async HTTP client
- `feedparser` - RSS/Atom feed parsing
- `PyMuPDF==1.26.5` - PDF text extraction

### Utilities
- `python-dotenv==1.0.0` - Environment variable management

## Development

### Running Tests
```bash
pytest tests/
```

### Project Structure Guidelines
- Client code: `src/client/`
- Server code: `src/server/src/arxiv_server/`
- Examples: `examples/`
- Tests: `tests/`

## Troubleshooting

### Common Issues

1. **"Server file does not exist"**
   - Set `ARXIV_SERVER_PATH` in `.env` to absolute path
   - Ensure path points to directory containing `server.py`

2. **Bedrock errors in Sampling**
   - Verify AWS credentials are configured
   - Check `AWS_REGION` and `BEDROCK_MODEL` in `.env`
   - Ensure Bedrock access is enabled in AWS account

3. **Download failures**
   - Verify `DOWNLOAD_PATH` exists and is writable
   - Check network connectivity to arXiv.org
   - Review SSL verification settings

4. **Connection errors**
   - Ensure server Python path is correct
   - Verify all dependencies are installed
   - Check server logs for detailed error messages

## Example Output

### Demo Session
```mermaid
flowchart TD
    A[User: python examples/demo.py] --> B[Environment Setup Check<br/>.env file loading]
    B --> C[MCPClient Initialization<br/>- Server configuration<br/>- Bedrock LLM setup<br/>- Roots setup]
    C --> D[Primitive Demos<br/>- Roots Demo<br/>- Sampling Demo]
    D --> E[MCPAgent Initialization<br/>client.initialize call]
    E --> F[MCPClient.connect<br/>- stdio connection<br/>- ClientSession creation<br/>- Server initialization]
    F --> G[Server Connected<br/>✅ Connected to MCP server]
    G --> H[Tool List Query<br/>list_tools call]
    H --> I[Interactive Menu<br/>1. Search arXiv<br/>2. Get Paper Details<br/>3. Download Article<br/>4. Exit]
    I --> J{User Selection}
    J -->|1| K[Search arXiv<br/>agent.search_arxiv]
    J -->|2| L[Get Paper Details<br/>agent.get_details]
    J -->|3| M[Download Article<br/>agent.download_article]
    J -->|4| N[Exit]
    K --> O[Display Results]
    L --> O
    M --> O
    O --> I
    N --> P[agent.close<br/>Connection closed]
```

## References

- [Model Context Protocol](https://modelcontextprotocol.io)
- [arXiv API Documentation](https://arxiv.org/help/api)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [arXiv MCP Server (blazickjp)](https://github.com/blazickjp/arxiv-mcp-server) - Server implementation used in this project