#!/usr/bin/env python3
"""Bundled MCP server entrypoint for Claude Code and Claude Desktop plugins."""

import os
import sys
from pathlib import Path

# Resolve plugin root and ensure bundled Python source modules are importable
PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parent.parent))
SRC_DIR = PLUGIN_ROOT / "src"

if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Ensure HATH0R group root is set if not already defined
if "HATH0R_GROUP_ROOT" not in os.environ:
    os.environ["HATH0R_GROUP_ROOT"] = str(PLUGIN_ROOT.parent)

try:
    from hath0r_cli.server.mcp_server import create_mcp_server
except ImportError:
    # Fallback to local import if needed
    sys.path.insert(0, str(PLUGIN_ROOT))
    from hath0r_cli.server.mcp_server import create_mcp_server


def main() -> None:
    server = create_mcp_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
