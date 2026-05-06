"""MCP server entry-point."""

from __future__ import annotations

import sys

from asf_policy_mcp.tools import mcp


def main() -> None:
    try:
        mcp.run()
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
