#!/usr/bin/env python3
"""Simple MCP server for testing purposes."""

from fastmcp import FastMCP

# Create server instance
mcp = FastMCP("test-server")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


@mcp.tool()
def multiply(x: int, y: int) -> int:
    """Multiply two numbers."""
    return x * y


@mcp.tool()
def get_weather(city: str) -> str:
    """Get weather for a city (mock implementation)."""
    return f"Weather in {city}: Sunny, 22°C"


@mcp.tool()
def echo(message: str) -> str:
    """Echo back the message."""
    return f"Echo: {message}"


@mcp.tool()
def divide(numerator: float, denominator: float) -> float:
    """Divide two numbers."""
    if denominator == 0:
        raise ValueError("Cannot divide by zero")
    return numerator / denominator


if __name__ == "__main__":
    # Run the server
    mcp.run()
