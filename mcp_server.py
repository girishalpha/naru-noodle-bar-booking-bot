"""
Naru Booking Bot - MCP Server
Exposes restaurant booking as tools callable by any AI (Claude, GPT, etc.)

SETUP:
    pip install fastmcp camoufox[geoip]
    camoufox fetch

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

    Or for remote SSE:
    {
      "mcpServers": {
        "naru-booking": {
          "url": "http://your-server:8080/sse"
        }
      }
    }
"""

import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastmcp import FastMCP
from camoufox.async_api import AsyncCamoufox

# ================================================================
# MCP SERVER
# ================================================================

mcp = FastMCP(
    "Naru Booking Bot",
    description="Book tables at Naru Noodle Bar / Cafe Air restaurants. "
    "Handles the full flow: date, seating, time slot, guests, form, and Razorpay payment.",
)

SLOT_MAP = {"12:30": "12:30 PM", "14:30": "02:30 PM", "18:30": "06:30 PM", "20:30": "08:30 PM"}

# Store last booking result for status checks
_last_result = {"status": "idle", "details": ""}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("mcp-booking")


@mcp.tool
def get_available_slots() -> dict:
    """Get available booking slots and seating options.

    Returns the valid time slots, seating types, and other booking parameters.
    Call this first to know what options are available before making a booking.
    """
    return {
        "slots": list(SLOT_MAP.keys()),
        "slots_display": SLOT_MAP,
        "seating_options": ["RAMEN", "TABLE"],
        "max_guests": 4,
        "booking_url": "https://bookings.airmenus.in/CafeAir/CafeAir/",
        "notes": {
            "RAMEN": "Ramen Bar Seating - INR 1000/person, redeemable against food bill",
            "TABLE": "Table seating (seats 4) - INR 5000/table, redeemable against food bill",
        },
    }


@mcp.tool
def get_booking_status() -> dict:
    """Check the status of the last booking attempt.

    Returns the current status and any details about the booking process.
    """
    return _last_result


@mcp.tool
async def book_restaurant(
    name: str,
    email: str,
    phone: str,
    slot: str,
    seating: str = "RAMEN",
    guests: int = 2,
    target_date: Optional[str] = None,
    special_requests: str = "",
    booking_url: str = "https://bookings.airmenus.in/CafeAir/CafeAir/",
) -> dict:
    """Book a table at Naru Noodle Bar / Cafe Air.

    This launches a stealth browser, navigates the booking flow, fills the form,
    and attempts to complete payment via Amazon Pay wallet on Razorpay.

    Args:
        name: Full name for the reservation
        email: Email address for confirmation
        phone: 10-digit Indian phone number (no +91 prefix)
        slot: Time slot - must be one of: 12:30, 14:30, 18:30, 20:30
        seating: RAMEN (bar seating, INR 1000/person) or TABLE (INR 5000/table)
        guests: Number of guests (1-4)
        target_date: Date in YYYY-MM-DD format (defaults to tomorrow)
        special_requests: Any special requests for the restaurant
        booking_url: The booking page URL (has a default)

    Returns:
        dict with status (success/partial/failed), details, and payment_url if manual payment needed
    """
    global _last_result
    _last_result = {"status": "running", "details": "Starting booking..."}

    # Validate inputs
    if slot not in SLOT_MAP:
        return {"status": "error", "details": f"Invalid slot. Must be one of: {list(SLOT_MAP.keys())}"}
    if not phone.isdigit() or len(phone) != 10:
        return {"status": "error", "details": "Phone must be exactly 10 digits"}
    if seating.upper() not in ("RAMEN", "TABLE"):
        return {"status": "error", "details": "Seating must be RAMEN or TABLE"}
    if guests < 1 or guests > 4:
        return {"status": "error", "details": "Guests must be 1-4"}

    seating = seating.upper()
    if not target_date:
        target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        result = await _execute_booking(
            booking_url=booking_url,
            name=name,
            email=email,
            phone=phone,
            slot=slot,
            seating=seating,
            guests=guests,
            target_date=target_date,
            special_requests=special_requests,
        )
        _last_result = result
        return result
    except Exception as e:
        _last_result = {"status": "failed", "details": str(e)}
        return _last_result


async def _execute_booking(**cfg) -> dict:
    """Run the actual booking flow in a stealth browser."""
    log.info(f"Booking: {cfg['slot']} | {cfg['seating']} | {cfg['guests']} guests | {cfg['target_date']}")

    async with AsyncCamoufox(headless=True, humanize=True, os="windows") as browser:
        page = await browser.new_page()
        payment_url = None

        try:
            await page.goto(cfg["booking_url"], wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            # 1. Select date
            day = str(datetime.strptime(cfg["target_date"], "%Y-%m-%d").day)
            await page.evaluate("window.scrollBy(0, 300)")
            await page.wait_for_timeout(800)
            for btn in await page.locator("button").all():
                if (await btn.text_content() or "").strip() == day and await btn.is_visible():
                    await btn.click()
                    break
            else:
                return {"status": "failed", "details": f"Day {day} not found in calendar"}
            await page.wait_for_timeout(1000)
            log.info(f"  [1/8] Date selected: day {day}")

            # 2. Select seating
            keyword = "RAMEN BAR" if cfg["seating"] == "RAMEN" else "TABLE"
            await page.evaluate("window.scrollBy(0, 400)")
            await page.wait_for_timeout(800)
            card_xpath = f"//*[contains(text(),'{keyword}')]/ancestor::*[.//button[contains(text(),'BOOK')]]"
            card = page.locator(card_xpath).first
            if await card.count() > 0:
                await card.locator("button", has_text="BOOK").first.click()
            else:
                await page.locator("button", has_text="BOOK").first.click()
            await page.wait_for_timeout(2000)
            log.info(f"  [2/8] Seating: {keyword}")

            # 3. Select time slot
            slot_text = SLOT_MAP[cfg["slot"]]
            await page.wait_for_timeout(1500)
            slot_loc = page.locator(f"text='{slot_text}'").first
            if await slot_loc.count() > 0 and await slot_loc.is_visible():
                await slot_loc.click()
            else:
                pattern = slot_text.replace(" ", "\\s*")
                slot2 = page.locator(f"text=/{pattern}/i").first
                if await slot2.count() > 0:
                    await slot2.click()
                else:
                    await page.locator("text=/\\d+:\\d+\\s*PM/i").first.click()
                    log.warning("  Desired slot unavailable, picked first available")
            await page.wait_for_timeout(1000)
            log.info(f"  [3/8] Slot: {slot_text}")

            # 4. Set guests
            clicks = cfg["guests"] - 1
            if clicks > 0:
                plus = page.locator("button", has_text="+").first
                await plus.wait_for(timeout=5000)
                for _ in range(clicks):
                    await plus.click()
                    await page.wait_for_timeout(300)
            log.info(f"  [4/8] Guests: {cfg['guests']}")

            # 5. CONTINUE
            await page.locator("button", has_text="CONTINUE").first.click()
            await page.wait_for_timeout(3000)
            log.info("  [5/8] CONTINUE clicked")

            # 6. Fill form
            await page.wait_for_timeout(2000)
            await page.locator("input[type='text'], input[placeholder*='name' i]").first.fill(cfg["name"])
            await page.locator("input[type='email'], input[placeholder*='email' i]").first.fill(cfg["email"])
            await page.locator("input[type='tel'], input[type='number'], input[placeholder*='mobile' i]").first.fill(cfg["phone"])
            if cfg["special_requests"]:
                ta = page.locator("textarea").first
                if await ta.count() > 0:
                    await ta.fill(cfg["special_requests"])
            cb = page.locator("input[type='checkbox']").first
            if await cb.count() > 0 and not await cb.is_checked():
                await cb.click()
            await page.wait_for_timeout(1000)
            log.info("  [6/8] Form filled")

            # 7. PROCEED
            await page.locator("button", has_text="PROCEED").first.click()
            await page.wait_for_timeout(5000)
            log.info("  [7/8] PROCEED clicked")

            # 8. Payment
            log.info("  [8/8] Payment (Razorpay)...")
            payment_url = page.url

            # Try Razorpay iframe
            ctx = page
            try:
                frame = page.frame_locator("iframe[class*='razorpay'], iframe[src*='razorpay']")
                if await frame.locator("text=Wallet").count() > 0:
                    ctx = frame
            except Exception:
                pass

            try:
                await ctx.locator("text=Wallet").first.wait_for(timeout=15000)
                await ctx.locator("text=Wallet").first.click()
                await page.wait_for_timeout(2000)
                await ctx.locator("text=Amazon Pay").first.click()
                await page.wait_for_timeout(2000)

                pay_btn = ctx.locator("button:has-text('Pay'), button[id*='pay']").first
                if await pay_btn.count() > 0:
                    await pay_btn.click()
                    await page.wait_for_timeout(5000)

                # Check result
                current_url = page.url
                if "amazon" in current_url.lower():
                    return {
                        "status": "partial",
                        "details": "Amazon Pay requires OTP/login. Browser is headless so manual completion needed.",
                        "payment_url": current_url,
                    }

                success = page.locator("text=/success|confirmed|booked/i").first
                if await success.count() > 0:
                    return {"status": "success", "details": "Booking confirmed and payment completed!"}

                return {
                    "status": "partial",
                    "details": "Payment initiated via Amazon Pay. Check email for confirmation.",
                    "payment_url": current_url,
                }

            except Exception as e:
                payment_url = page.url
                await page.screenshot(path="logs/payment_page.png")
                return {
                    "status": "partial",
                    "details": f"Booking submitted but payment needs manual completion: {e}",
                    "payment_url": payment_url,
                    "screenshot": "logs/payment_page.png",
                }

        except Exception as e:
            await page.screenshot(path="logs/mcp_error.png")
            return {
                "status": "failed",
                "details": str(e),
                "screenshot": "logs/mcp_error.png",
                "payment_url": payment_url,
            }


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
