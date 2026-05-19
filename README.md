# Naru Noodle Bar / Cafe Air - Booking Bot

Automated restaurant booking using **Camoufox** (stealth Firefox browser with zero CDP leaks) and **Razorpay** payment automation. Includes an MCP server so any AI assistant can book for you.

## Why Camoufox?

Most booking sites use bot detection (Akamai, reCAPTCHA, Cloudflare). Traditional Selenium/Playwright gets flagged instantly because of CDP (Chrome DevTools Protocol) leaks. Camoufox is Firefox-based - entire classes of CDP detection simply don't apply. Zero captchas, even against aggressive protection.

## Project Structure

```
booking_bot.py   - Interactive CLI bot (asks for your details, runs booking)
mcp_server.py    - MCP server (any AI can call it via tools)
logs/            - Auto-created: timestamped logs + error screenshots
```

---

## Quick Start (Interactive CLI)

### Prerequisites

- Python 3.10+
- Internet connection

### Install & Run

```bash
# Install dependencies
pip install camoufox[geoip]

# Download the Camoufox browser binary (one-time, ~80MB)
camoufox fetch

# Run the bot
python booking_bot.py
```

### What Happens

The bot will ask you for:

```
==============================================
   NARU / CAFE AIR -- BOOKING BOT SETUP
==============================================

  Booking URL [https://bookings.airmenus.in/CafeAir/CafeAir/]:
  Your full name: John Doe
  Email: john@example.com
  Phone (10 digits, no +91): 9876543210
  Number of guests (1-4) [2]: 2

  Available slots: 12:30 | 14:30 | 18:30 | 20:30
  Preferred time slot [20:30]: 20:30
  Seating options: RAMEN | TABLE
  Seating preference [RAMEN]: RAMEN
  Target date (YYYY-MM-DD, empty=tomorrow) [2026-05-20]: 2026-05-25
  Special requests (optional):
  Run headless? (y/n) [n]: n

  > Config ready: 20:30 | RAMEN | 2 guests | 2026-05-25
  > Log file: logs/booking_20260519_160000.log

  Start booking? (y/n) [y]: y
```

Then it:
1. Opens stealth Firefox (you can watch it work)
2. Selects your date from the calendar
3. Clicks BOOK on your seating preference
4. Selects your time slot
5. Sets guest count
6. Fills the reservation form (name, email, phone, T&C)
7. Clicks PROCEED to payment
8. Auto-selects Wallet > Amazon Pay on Razorpay
9. Browser stays open for you to complete OTP if needed

---

## MCP Server (for AI Agents)

The MCP server lets any AI assistant (Claude, GPT, Gemini, Cursor, etc.) book restaurants for you by calling tools.

### Install & Run

```bash
# Install both packages
pip install fastmcp camoufox[geoip]
camoufox fetch

# Run locally (stdio mode - for Claude Desktop, Cursor, Kiro, etc.)
python mcp_server.py

# Run as remote server (SSE mode - for deployed instances)
python mcp_server.py --sse --port 8080
```

### Connect to Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "naru-booking": {
      "command": "python",
      "args": ["C:/full/path/to/mcp_server.py"]
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

### Available Tools

| Tool | Description |
|------|-------------|
| `get_available_slots` | Returns valid time slots, seating options, pricing info |
| `book_restaurant` | Runs the full booking flow with provided details |
| `get_booking_status` | Check status of the last booking attempt |

### Tool: `get_available_slots`

No parameters needed. Returns:

```json
{
  "slots": ["12:30", "14:30", "18:30", "20:30"],
  "seating_options": ["RAMEN", "TABLE"],
  "max_guests": 4,
  "notes": {
    "RAMEN": "Ramen Bar Seating - INR 1000/person, redeemable against food bill",
    "TABLE": "Table seating (seats 4) - INR 5000/table, redeemable against food bill"
  }
}
```

### Tool: `book_restaurant`

Parameters:

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Full name for reservation |
| `email` | string | yes | Email for confirmation |
| `phone` | string | yes | 10-digit Indian phone number |
| `slot` | string | yes | Time: 12:30, 14:30, 18:30, or 20:30 |
| `seating` | string | no | RAMEN (default) or TABLE |
| `guests` | int | no | 1-4 (default: 2) |
| `target_date` | string | no | YYYY-MM-DD (default: tomorrow) |
| `special_requests` | string | no | Any special requests |

Returns:

```json
{
  "status": "success",
  "details": "Booking confirmed and payment completed!"
}
```

Or if manual payment is needed:

```json
{
  "status": "partial",
  "details": "Amazon Pay requires OTP/login.",
  "payment_url": "https://..."
}
```

### Example AI Conversation

**User:** "Book me a table at Naru for 2 people this Saturday at 8:30 PM, ramen bar seating"

**AI:** *calls `get_available_slots`* to verify options, then *calls:*

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "9876543210",
  "slot": "20:30",
  "seating": "RAMEN",
  "guests": 2,
  "target_date": "2026-05-24"
}
```

**AI:** "Your booking is confirmed! Ramen bar seating for 2 at 8:30 PM on May 24th."

---

## Payment Handling

The bot handles Razorpay's payment gateway:

1. **Detects Razorpay** - works with both iframe and full-page modes
2. **Selects Wallet > Amazon Pay** - auto-clicks through the payment flow
3. **If auto-debit works** - returns `status: success`
4. **If OTP/login needed** - returns `status: partial` with the `payment_url` so you can complete it
5. **If payment fails** - saves screenshot to `logs/payment_page.png` and returns the URL

---

## Logging

All runs create timestamped log files:

```
logs/
  booking_20260519_160000.log    - Full step-by-step log
  error_attempt_1.png            - Screenshot on failure
  payment_page.png               - Payment page screenshot (if manual needed)
```

- Rotating files: 5MB max, keeps last 5 logs
- Both console output and file logging
- Every step logged with timestamps

---

## Deployment

### On a VPS / Cloud Server

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y python3.10 python3-pip

# Install
pip install fastmcp camoufox[geoip]
camoufox fetch

# Run MCP server (SSE mode for remote access)
python mcp_server.py --sse --port 8080

# Or run with nohup for persistence
nohup python mcp_server.py --sse --port 8080 &
```

### Docker

```dockerfile
FROM python:3.10-slim
RUN pip install fastmcp camoufox[geoip] && python -m camoufox fetch
COPY booking_bot.py mcp_server.py ./
EXPOSE 8080
CMD ["python", "mcp_server.py", "--sse", "--port", "8080"]
```

### Headless Mode

- CLI bot: answer `y` to "Run headless?" prompt
- MCP server: always runs headless automatically
- Linux servers: uses Xvfb virtual display via `headless="virtual"`

---

## Seating & Pricing

| Option | Price | Details |
|--------|-------|---------|
| Ramen Bar Seating | INR 1,000/person | Redeemable against food bill. Max 3 per booking. |
| Table (Seats 4) | INR 5,000/table | Redeemable against food bill. Full table booking. |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `camoufox fetch` fails | Check internet connection, try with `--force` flag |
| Bot can't find date | Ensure `TARGET_DATE` is a future date that's available |
| Slot sold out | Bot picks first available slot and logs a warning |
| Payment timeout | Check `logs/payment_page.png` and use the URL manually |
| Import errors | Ensure Python 3.10+ and run `pip install camoufox[geoip]` |

---

## Tech Stack

| Component | Purpose |
|-----------|---------|
| [Camoufox](https://camoufox.com) | Anti-detect Firefox browser (no CDP leaks) |
| [Playwright](https://playwright.dev/python/) | Browser automation API (async) |
| [FastMCP](https://gofastmcp.com) | MCP server framework |
| Python asyncio | Async execution |

---

## License

MIT
