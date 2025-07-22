from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Calculator")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers"""
    return a + b


if __name__ == "__main__":
    print("====== START ======")

    mcp.run(transport="streamable-http")

    print("======  END  ======")
