
import asyncio
import os
import sys

from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import (
    stdio_client,
    StdioServerParameters
)


BASE_DIR = Path(__file__).resolve().parents[1]


async def main():

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        cwd=str(BASE_DIR),
        env=os.environ.copy()
    )

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            # Initialize MCP connection
            await session.initialize()

            print("\nMCP server connected!\n")

            # Discover available tools
            tools = await session.list_tools()

            print("Available MCP tools:")

            for tool in tools.tools:
                print("-", tool.name)

            # Test 1: List files
            print("\n--- LIST FILES ---")

            result = await session.call_tool(
                "list_files",
                {}
            )

            print(result.content)

            print("\n--- COUNT FILES ---")

            result = await session.call_tool(
                "count_files",
                {}
            )

            print(result.content)

            # Test 2: Repository structure
            print("\n--- FILE STRUCTURE ---")

            result = await session.call_tool(
                "get_file_structure",
                {}
            )

            print(result.content)

            # Test 3: Search code
            print("\n--- SEARCH CODE ---")

            result = await session.call_tool(
                "search_code",
                {"keyword": "def"}
            )

            print(result.content[:3] if isinstance(
                result.content, list
            ) else result.content)

            # Test 4: Read a file
            print("\n--- READ FILE ---")

            result = await session.call_tool(
                "read_file",
                {"file_path": "documents/readme.md"}
            )

            print(result.content)

            print("\nAll MCP tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
