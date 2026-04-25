#!/usr/bin/env bash
# Wrapper for Claude Code to spawn the searxng MCP server. Activates the
# repo's venv so dependencies are isolated. Stdin/stdout passes through to
# the python process for MCP's JSON-RPC.

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/.venv/bin/python" "$DIR/server.py"
