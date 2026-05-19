# Naru Noodle Bar / Cafe Air - Booking Bot

Stealth booking bot using [Camoufox](https://camoufox.com) + Razorpay payment automation.
Includes an **MCP server** so any AI (Claude, GPT, Gemini, etc.) can book for you.

## Quick Start (Interactive CLI)

```bash
pip install camoufox[geoip]
camoufox fetch
python booking_bot.py
```

## MCP Server (for AI Agents)

```bash
pip install fastmcp camoufox[geoip]
camoufox fetch

# Local (stdio - for Claude Desktop, Cursor, etc.)
python mcp_server.py

# Remote (SSE - for deployed servers)
python mcp_server.py --sse --port 8080
```

### Connect to Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "naru-booking": {
      "command": "python",
      "args": ["C:/path/to/mcp_server.py"]
    }
  }
}
```

### Connect to Remote Server

```json
{
  "mcpServers": {
    "naru-booking": {
      "url": "http://your-server:8080/sse"
    }
  }
}
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `get_available_slots` | Returns valid slots, seating options, pricing |
| `book_restaurant` | Full booking flow (date, seating, time, form, payment) |
| `get_booking_status` | Check status of last booking attempt |

### Example AI Conversation

> "Book me a table at Naru for 2 people this Saturday at 8:30 PM"

The AI will call `get_available_slots` to check options, then `book_restaurant` with your details.

## Payment Handling

- Auto-selects **Wallet > Amazon Pay** on Razorpay
- If payment completes: returns `status: success`
- If OTP needed: returns `status: partial` + `payment_url` for manual completion
- If payment fails: returns screenshot path + URL

## Files

```
booking_bot.py   - Interactive CLI bot (run manually)
mcp_server.py    - MCP server (connect any AI)
logs/            - Auto-created logs + error screenshots
```

## Deploy

Works on any server with Python 3.10+:

```bash
# On your VPS/cloud instance:
pip install fastmcp camoufox[geoip]
camoufox fetch
python mcp_server.py --sse --port 8080
```

Then point your AI client to `http://your-server:8080/sse`.
