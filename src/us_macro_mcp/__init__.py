"""
US-Macro-MCP - the package entry point.

What this file does, in order:
1. Exposes the version number to anything that imports this package.
2. Defines main(), the command the operating system runs when someone types "us-macro-mcp".
3. main() starts the MCP server, which then waits for an AI client to connect and call its tools.
"""

from __future__ import annotations

__version__ = "0.1.2"


# The command line entry point: starts the MCP server and hands control to it.
def main() -> None:
    from .server import run

    run()


__all__ = ["main", "__version__"]
