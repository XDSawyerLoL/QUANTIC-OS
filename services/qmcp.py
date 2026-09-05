#!/usr/bin/env python3
"""Compatibility entry point for the Quantic MCP gateway.

The final remaster validation historically expects services/qmcp.py, while the
actual implementation lives in qmcp_gateway.py. Re-export the gateway API so
both names remain valid without duplicating logic.
"""
from qmcp_gateway import MCPServer, ROOT, authorize, discover, load

__all__ = ["MCPServer", "ROOT", "authorize", "discover", "load"]
