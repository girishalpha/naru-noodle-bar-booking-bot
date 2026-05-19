"""
Naru Booking Bot - MCP Server
Exposes restaurant booking as tools callable by any AI (Claude, GPT, etc.)

SETUP:
    pip install -r requirements.txt
    playwright install firefox

RUN:
    python mcp_server.py                    # stdio (for local AI clients)
    python mcp_server.py --sse              # SSE (for remote/deployed servers)
    python mcp_server.py --sse --port 8080  # custom port

CONNECT FROM AI CLIENT (e.g. Claude Desktop config):
    {
      "mcpServers": {
        "naru-booking": {
          "command": "python",
          "args": ["path/to/mcp_server.py"]
        }
      }
    }
"""

import os
import sys
import logging
from typing import Optional
from mcp.server.fastmcp import FastMCP

from engine import BookingConfig, BookingResult, run_booking, validate_config, SLOT_MAP, SEATING_MAP, VALID_SEATING, BOOKING_URL

# ================================================================
# MCP SERVER
# ================================================================

mcp = FastMCP("Naru Booking Bot")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("naru.mcp")

# Store last booking result for status checks
_last_result: dict = {"status": "idle", "details": "No booking attempted yet"}


@mcp.tool()
def get_available_slots() -> dict:
    """Get available booking slots and seating options.

    Returns the valid time slots, seating types, and other booking parameters.
    Call this first to know what options are available before making a booking.
    """
    return {
        "slots": list(SLOT_MAP.keys()),
        "slots_display": SLOT_MAP,
        "seating_options": VALID_SEATING,
        "seating_details": SEATING_MAP,
        "max_guests": 5,
        "booking_url": BOOKING_URL,
        "notes": {
            "TABLE2": "Table for 2 guests",
            "TABLE3": "Table for 3 guests",
            "SOFA": "Sofa seating - fits 3-5 guests (cosy at 5)",
            "COMMUNITY": "Community seating - book 4 for private use, otherwise shared",
            "DINNER": "Dinner seating",
        },
    }


@mcp.tool()
def get_booking_status() -> dict:
    """Check the status of the last booking attempt.

    Returns the current status and any details about the booking process.
    """
    return _last_result


@mcp.tool()
async def book_restaurant(
    name: str,
    email: str,
    phone: str,
    slot: str,
    seating: str = "TABLE2",
    guests: int = 2,
    target_date: Optional[str] = None,
    special_requests: str = "",
) -> dict:
    """Book a table at Cafe Air (Double Dashi).

    This launches a stealth browser, navigates the booking flow, fills the form,
    and attempts to complete payment via Razorpay.

    Args:
        name: Full name for the reservation
        email: Email address for confirmation
        phone: 10-digit Indian phone number (no +91 prefix)
        slot: Time slot in HH:MM 24h format (e.g. 19:00, 21:30)
        seating: One of TABLE2, TABLE3, SOFA, COMMUNITY, DINNER
        guests: Number of guests (1-5)
        target_date: Date in YYYY-MM-DD format (defaults to tomorrow)
        special_requests: Any special requests for the restaurant

    Returns:
        dict with status (success/partial/failed), message, and payment_url if manual payment needed
    """
    global _last_result
    _last_result = {"status": "running", "message": "Starting booking..."}

    cfg = BookingConfig(
        name=name,
        email=email,
        phone=phone,
        slot=slot,
        seating=seating,
        guests=guests,
        target_date=target_date or "",
        special_requests=special_requests,
        headless=True,  # MCP always runs headless
    )

    error = validate_config(cfg)
    if error:
        _last_result = {"status": "error", "message": error}
        return _last_result

    try:
        result = await run_booking(cfg)
        _last_result = result.to_dict()
        return _last_result
    except Exception as e:
        _last_result = {"status": "failed", "message": str(e)}
        return _last_result


# ================================================================
# ENTRY POINT
# ================================================================

if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)

    if "--sse" in sys.argv:
        port = 8080
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
        print(f"Starting MCP server (SSE) on http://0.0.0.0:{port}/sse")
        mcp.run(transport="sse", host="0.0.0.0", port=port)
    else:
        mcp.run()
