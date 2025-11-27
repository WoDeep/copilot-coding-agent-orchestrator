"""
MCP Client for GitHub Copilot Integration
Connects to the GitHub Remote MCP server to assign issues to Copilot

Uses the official GitHub MCP Server (remote) at https://api.githubcopilot.com/mcp/
This server includes the 'copilot' toolset with Copilot Coding Agent tools.
"""

import asyncio
import json
import os
import logging
import httpx
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_env():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    if value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    os.environ[key] = value

load_env()


@dataclass
class MCPToolResult:
    """Result from an MCP tool call"""
    success: bool
    content: Any
    error: Optional[str] = None


class GitHubMCPClient:
    """
    MCP Client that connects to the GitHub Remote MCP Server via HTTP.
    
    The remote server at https://api.githubcopilot.com/mcp/ provides:
    - copilot toolset: Copilot Coding Agent tools (assign_copilot_to_issue)
    - Plus all standard GitHub tools (repos, issues, pull_requests, etc.)
    
    Requires session management via Mcp-Session-Id header.
    """
    
    # Remote GitHub MCP Server endpoint
    MCP_SERVER_URL = "https://api.githubcopilot.com/mcp/"
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable required")
        
        self._session_id: Optional[str] = None
        self._request_id: int = 0
        self.client: Optional[httpx.AsyncClient] = None
    
    def _get_headers(self) -> dict[str, str]:
        """Get headers for MCP requests"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers
    
    def _next_request_id(self) -> int:
        """Get next JSON-RPC request ID"""
        self._request_id += 1
        return self._request_id
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def initialize(self) -> bool:
        """Initialize the MCP session"""
        if not self.client:
            self.client = httpx.AsyncClient(timeout=60.0)
        
        # Generate initial session ID
        import uuid
        self._session_id = str(uuid.uuid4())
        
        try:
            response = await self.client.post(
                self.MCP_SERVER_URL,
                headers=self._get_headers(),
                json={
                    "jsonrpc": "2.0",
                    "id": self._next_request_id(),
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "TimeAttack-Automation",
                            "version": "1.0.0"
                        }
                    }
                }
            )
            
            if response.status_code == 200:
                # Server may return a different session ID
                returned_session = response.headers.get("Mcp-Session-Id")
                if returned_session:
                    self._session_id = returned_session
                
                result = response.json()
                server_info = result.get('result', {}).get('serverInfo', {})
                logger.info(f"MCP Server initialized: {server_info.get('name')} v{server_info.get('version')}")
                logger.info(f"Session ID: {self._session_id}")
                return True
            else:
                logger.error(f"Failed to initialize: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Initialize error: {e}")
            return False
    
    async def close(self):
        """Close the client"""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    async def list_tools(self) -> list[dict]:
        """List all available tools from the MCP server"""
        if not self.client or not self._session_id:
            raise RuntimeError("Not initialized. Use 'async with GitHubMCPClient():'")
        
        try:
            response = await self.client.post(
                self.MCP_SERVER_URL,
                headers=self._get_headers(),
                json={
                    "jsonrpc": "2.0",
                    "id": self._next_request_id(),
                    "method": "tools/list",
                    "params": {}
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                tools = result.get("result", {}).get("tools", [])
                return tools
            else:
                logger.error(f"Failed to list tools: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"List tools error: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Call a tool on the MCP server"""
        if not self.client or not self._session_id:
            raise RuntimeError("Not initialized. Use 'async with GitHubMCPClient():'")
        
        try:
            response = await self.client.post(
                self.MCP_SERVER_URL,
                headers=self._get_headers(),
                json={
                    "jsonrpc": "2.0",
                    "id": self._next_request_id(),
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if "error" in result:
                    return MCPToolResult(
                        success=False,
                        content=None,
                        error=result["error"].get("message", "Unknown error")
                    )
                return MCPToolResult(
                    success=True,
                    content=result.get("result", {})
                )
            else:
                return MCPToolResult(
                    success=False,
                    content=None,
                    error=f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            return MCPToolResult(
                success=False,
                content=None,
                error=str(e)
            )
    
    async def assign_copilot_to_issue(
        self, 
        owner: str, 
        repo: str, 
        issue_number: int
    ) -> MCPToolResult:
        """
        Assign GitHub Copilot to an issue using the MCP server's tool.
        
        This uses the 'copilot' toolset available in the remote GitHub MCP Server.
        
        Args:
            owner: Repository owner (e.g., 'WoDeep')
            repo: Repository name (e.g., 'TimeAttack')
            issue_number: Issue number to assign
            
        Returns:
            MCPToolResult with success status and content
        """
        logger.info(f"Assigning Copilot to issue #{issue_number} in {owner}/{repo}")
        
        # The tool name in the remote server
        result = await self.call_tool(
            "assign_copilot_to_issue",
            {
                "owner": owner,
                "repo": repo,
                "issueNumber": issue_number
            }
        )
        
        if result.success:
            logger.info(f"Successfully assigned Copilot to issue #{issue_number}")
        else:
            logger.error(f"Failed to assign Copilot: {result.error}")
        
        return result


async def assign_copilot(owner: str, repo: str, issue_number: int) -> bool:
    """
    High-level function to assign Copilot to an issue.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        async with GitHubMCPClient() as client:
            # First list tools to see what's available
            tools = await client.list_tools()
            tool_names = [t.get("name", "") for t in tools]
            logger.info(f"Available tools: {tool_names}")
            
            # Check if the copilot assignment tool is available
            copilot_tools = [t for t in tool_names if "copilot" in t.lower()]
            if copilot_tools:
                logger.info(f"Copilot tools found: {copilot_tools}")
            
            # Try to assign
            result = await client.assign_copilot_to_issue(owner, repo, issue_number)
            return result.success
            
    except Exception as e:
        logger.error(f"Failed to assign Copilot: {e}")
        return False


def assign_copilot_sync(owner: str, repo: str, issue_number: int) -> bool:
    """
    Synchronous wrapper for assign_copilot.
    Use this from non-async code.
    """
    return asyncio.run(assign_copilot(owner, repo, issue_number))


# CLI interface
if __name__ == "__main__":
    import sys
    
    async def main():
        if len(sys.argv) < 2:
            print("Usage:")
            print("  python mcp_client.py list-tools")
            print("  python mcp_client.py assign <owner> <repo> <issue_number>")
            print("")
            print("Examples:")
            print("  python mcp_client.py list-tools")
            print("  python mcp_client.py assign WoDeep TimeAttack 197")
            sys.exit(1)
        
        command = sys.argv[1]
        
        if command == "list-tools":
            async with GitHubMCPClient() as client:
                tools = await client.list_tools()
                print(f"\nFound {len(tools)} tools:\n")
                for tool in tools:
                    name = tool.get("name", "unknown")
                    desc = tool.get("description", "")[:80]
                    print(f"  • {name}")
                    if desc:
                        print(f"    {desc}")
                
                # Highlight copilot tools
                copilot_tools = [t for t in tools if "copilot" in t.get("name", "").lower()]
                if copilot_tools:
                    print(f"\n🤖 Copilot tools: {[t.get('name') for t in copilot_tools]}")
        
        elif command == "assign":
            if len(sys.argv) < 5:
                print("Usage: python mcp_client.py assign <owner> <repo> <issue_number>")
                sys.exit(1)
            
            owner = sys.argv[2]
            repo = sys.argv[3]
            issue_number = int(sys.argv[4])
            
            success = await assign_copilot(owner, repo, issue_number)
            sys.exit(0 if success else 1)
        
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    
    asyncio.run(main())
