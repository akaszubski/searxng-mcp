# searxng-mcp

Tiny MCP server that exposes web `search` and page `fetch` tools backed by a
local SearXNG container. Replaces Anthropic's `WebSearch` for clients pointed
at a local LLM server (where Anthropic's server-side tools don't fire).

## Why

Anthropic's `WebSearch` is a *server-side* tool — when Claude Code talks to
api.anthropic.com it routes there, when it talks to vllm-mlx (or any local
OpenAI-compatible server) it gets 0 results. This MCP server gives Claude
Code real tools (`mcp__searxng__search`, `mcp__searxng__fetch`) backed by
your own SearXNG, so research works the same way locally.

## Prereqs

- Docker (or OrbStack) for the SearXNG backend
- Python 3.10+ for the MCP server

## Install (per machine)

This repo lives inside the [`local-claude-code-mlx`](../) umbrella, but
works standalone too. From the umbrella root (or wherever you cloned it):

```bash
cd searxng-mcp

# 1. Start SearXNG in a container (loopback :8080).
#    Container is named `localclaude-searxng` with `restart: unless-stopped`,
#    so it auto-comes-back across reboots once OrbStack/Docker is up.
docker compose up -d

# 2. Install MCP server deps in a venv
python3 -m venv .venv
.venv/bin/pip install mcp httpx

# 3. Sanity check both are alive
curl -sf -o /dev/null http://127.0.0.1:8080/ && echo "SearXNG up"
./run.sh < /dev/null > /dev/null 2>&1 && echo "MCP server starts cleanly"
```

Standalone install:

```bash
git clone https://github.com/akaszubski/searxng-mcp ~/Dev/searxng-mcp
cd ~/Dev/searxng-mcp
# then steps 1-3 above
```

## Register with Claude Code

```bash
claude mcp add searxng -- "$(pwd)/run.sh"   # run from inside searxng-mcp/
```

Or explicit path:

```bash
claude mcp add searxng -- ~/Dev/local-claude-code-mlx/searxng-mcp/run.sh
```

Or add manually to `~/.claude.json` under the `mcpServers` key:

```json
{
  "mcpServers": {
    "searxng": {
      "command": "/Users/<you>/Dev/searxng-mcp/run.sh",
      "args": [],
      "env": {}
    }
  }
}
```

Restart Claude Code; the model now sees `mcp__searxng__search` and
`mcp__searxng__fetch` as tools.

## Configure

| Env var | Default | Notes |
|---|---|---|
| `SEARXNG_URL` | `https://searxng.docker.orb.local` | SearXNG endpoint (no trailing slash) |
| `SEARXNG_TIMEOUT` | `30` | HTTP timeout in seconds |
| `SEARXNG_VERIFY` | `0` | Set `1` for strict TLS verification |

## Tools

### `mcp__searxng__search(query, count=5, language="en")`

Returns a numbered list of results, each with title, URL, and snippet.

### `mcp__searxng__fetch(url, max_chars=8000)`

Fetches a URL, strips HTML, returns text. Truncates to `max_chars` (default 8K).

## Use with localclaude

The default `code` allowlist already includes `mcp__searxng__search` and
`mcp__searxng__fetch`, so no extra flags are needed:

```bash
localclaude start coder
```

`localclaude start` also auto-brings-up the OrbStack engine and the
`localclaude-searxng` container if either is down — see
[`localclaude/README.md`](../localclaude/README.md#searxng-auto-start-behavior).

Use `-allowlist all` only if you want every MCP tool you've registered with
Claude Code to pass through (Gmail, Calendar, etc.) — at the cost of much
slower first-prefill.
