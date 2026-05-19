"""
Naru Noodle Bar / Cafe Air - Booking Bot
Stealth Firefox via Camoufox | Razorpay payment automation

SETUP:
    pip install camoufox[geoip]
    camoufox fetch
    python booking_bot.py
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from camoufox.async_api import AsyncCamoufox

# ================================================================
# LOGGING
# ================================================================

os.makedirs("logs", exist_ok=True)
log_file = f"logs/booking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=5),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("bot")

# ================================================================
# CONFIG (defaults - will be overridden by interactive prompts)
# ================================================================

SLOT_MAP = {"12:30": "12:30 PM", "14:30": "02:30 PM", "18:30": "06:30 PM", "20:30": "08:30 PM"}

DEFAULTS = {
    "BOOKING_URL": "https://bookings.airmenus.in/CafeAir/CafeAir/",
    "GUESTS": "2",
    "SLOT_PREFERENCE": "20:30",
    "SEATING_PREFERENCE": "RAMEN",
    "TARGET_DATE": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
    "HEADLESS": "n",
}


def ask(prompt, default="", validator=None):
    """Prompt user for input with optional default and validation."""
    while True:
        suffix = f" [{default}]" if default else ""
        val = input(f"  {prompt}{suffix}: ").strip() or default
        if validator:
            err = validator(val)
            if err:
                print(f"    ! {err}")
                continue
        return val


def collect_config():
    """Interactive config collection."""
    print("\n==============================================")
    print("   NARU / CAFE AIR -- BOOKING BOT SETUP")
    print("==============================================\n")

    cfg = {}
    cfg["BOOKING_URL"] = ask("Booking URL", DEFAULTS["BOOKING_URL"])
    cfg["USER_NAME"] = ask("Your full name", validator=lambda v: "Required" if not v else None)
    cfg["USER_EMAIL"] = ask("Email", validator=lambda v: "Must contain @" if "@" not in v else None)
    cfg["USER_PHONE"] = ask("Phone (10 digits, no +91)", validator=lambda v: "Must be 10 digits" if not (v.isdigit() and len(v) == 10) else None)
    cfg["GUESTS"] = ask("Number of guests (1-4)", DEFAULTS["GUESTS"], lambda v: "Must be 1-4" if not v.isdigit() or int(v) < 1 or int(v) > 4 else None)

    print(f"\n  Available slots: {' | '.join(SLOT_MAP.keys())}")
    cfg["SLOT_PREFERENCE"] = ask("Preferred time slot", DEFAULTS["SLOT_PREFERENCE"], lambda v: f"Must be one of {list(SLOT_MAP.keys())}" if v not in SLOT_MAP else None)

    print(f"  Seating options: RAMEN | TABLE")
    cfg["SEATING_PREFERENCE"] = ask("Seating preference", DEFAULTS["SEATING_PREFERENCE"], lambda v: "Must be RAMEN or TABLE" if v.upper() not in ("RAMEN", "TABLE") else None).upper()

    cfg["TARGET_DATE"] = ask("Target date (YYYY-MM-DD, empty=tomorrow)", DEFAULTS["TARGET_DATE"])
    cfg["SPECIAL_REQUESTS"] = ask("Special requests (optional)", "")

    headless = ask("Run headless? (y/n)", DEFAULTS["HEADLESS"])
    cfg["HEADLESS"] = headless.lower() in ("y", "yes", "true")

    print(f"\n  > Config ready: {cfg['SLOT_PREFERENCE']} | {cfg['SEATING_PREFERENCE']} | {cfg['GUESTS']} guests | {cfg['TARGET_DATE']}")
    print(f"  > Log file: {log_file}\n")

    confirm = input("  Start booking? (y/n) [y]: ").strip().lower() or "y"
    if confirm != "y":
        print("  Cancelled.")
        sys.exit(0)

    return cfg


# ================================================================
# BOT
# ================================================================

async def run_bot(cfg):
    log.info("Launching stealth browser...")

    async with AsyncCamoufox(headless=cfg["HEADLESS"], humanize=True, os="windows") as browser:
        page = await browser.new_page()

        for attempt in range(1, 4):
            try:
                log.info(f"=== Attempt {attempt}/3 ===")
                await page.goto(cfg["BOOKING_URL"], wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)

                await step_select_date(page, cfg)
                await step_select_seating(page, cfg)
                await step_select_time(page, cfg)
                await step_select_guests(page, cfg)
                await step_continue(page)
                await step_fill_form(page, cfg)
                await step_proceed(page)
                await step_payment(page)

                log.info("=== BOOKING COMPLETE ===")
                log.info(f"Full log saved to: {log_file}")
                await page.wait_for_timeout(120000)
                return

            except Exception as e:
                log.error(f"Attempt {attempt} failed: {e}")
                await page.screenshot(path=f"logs/error_attempt_{attempt}.png")
                log.info(f"  Screenshot saved: logs/error_attempt_{attempt}.png")
                if attempt < 3:
                    log.info("Retrying...")
                    await page.wait_for_timeout(2000)
                    await page.reload()
                    await page.wait_for_timeout(2000)
                else:
                    log.error("All attempts failed. Check logs/ folder for screenshots.")
                    await page.wait_for_timeout(30000)


async def step_select_date(page, cfg):
    log.info("[1/8] Selecting date...")
    target = cfg.get("TARGET_DATE", "")
    if target:
        day = str(datetime.strptime(target, "%Y-%m-%d").day)
    else:
        day = str((datetime.now() + timedelta(days=1)).day)

    await page.evaluate("window.scrollBy(0, 300)")
    await page.wait_for_timeout(800)

    for btn in await page.locator("button").all():
        if (await btn.text_content() or "").strip() == day and await btn.is_visible():
            await btn.click()
            log.info(f"  Selected day: {day}")
            await page.wait_for_timeout(1000)
            return
    raise Exception(f"Day {day} not found in calendar")


async def step_select_seating(page, cfg):
    keyword = "RAMEN BAR" if cfg["SEATING_PREFERENCE"] == "RAMEN" else "TABLE"
    log.info(f"[2/8] Selecting {keyword}...")
    await page.evaluate("window.scrollBy(0, 400)")
    await page.wait_for_timeout(800)

    card_xpath = f"//*[contains(text(),'{keyword}')]/ancestor::*[.//button[contains(text(),'BOOK')]]"
    card = page.locator(card_xpath).first
    if await card.count() > 0:
        await card.locator("button", has_text="BOOK").first.click()
    else:
        await page.locator("button", has_text="BOOK").first.click()
    log.info("  Clicked BOOK")
    await page.wait_for_timeout(2000)


async def step_select_time(page, cfg):
    slot_text = SLOT_MAP[cfg["SLOT_PREFERENCE"]]
    log.info(f"[3/8] Selecting slot {slot_text}...")
    await page.wait_for_timeout(1500)

    slot = page.locator(f"text='{slot_text}'").first
    if await slot.count() > 0 and await slot.is_visible():
        await slot.click()
        log.info(f"  Selected: {slot_text}")
    else:
        # Try regex match
        pattern = slot_text.replace(" ", "\\s*")
        slot2 = page.locator(f"text=/{pattern}/i").first
        if await slot2.count() > 0:
            await slot2.click()
            log.info(f"  Selected: {slot_text} (regex match)")
        else:
            await page.locator("text=/\\d+:\\d+\\s*PM/i").first.click()
            log.warning("  Desired slot unavailable - picked first available")
    await page.wait_for_timeout(1000)


async def step_select_guests(page, cfg):
    guests = int(cfg["GUESTS"])
    clicks = guests - 1
    log.info(f"[4/8] Setting guests to {guests}...")
    if clicks > 0:
        plus = page.locator("button", has_text="+").first
        await plus.wait_for(timeout=5000)
        for _ in range(clicks):
            await plus.click()
            await page.wait_for_timeout(300)
    log.info(f"  Guests: {guests}")
    await page.wait_for_timeout(500)


async def step_continue(page):
    log.info("[5/8] CONTINUE...")
    await page.locator("button", has_text="CONTINUE").first.click()
    await page.wait_for_timeout(3000)


async def step_fill_form(page, cfg):
    log.info("[6/8] Filling form...")
    await page.wait_for_timeout(2000)

    await page.locator("input[type='text'], input[placeholder*='name' i]").first.fill(cfg["USER_NAME"])
    await page.locator("input[type='email'], input[placeholder*='email' i]").first.fill(cfg["USER_EMAIL"])
    await page.locator("input[type='tel'], input[type='number'], input[placeholder*='mobile' i]").first.fill(cfg["USER_PHONE"])

    if cfg.get("SPECIAL_REQUESTS"):
        ta = page.locator("textarea").first
        if await ta.count() > 0:
            await ta.fill(cfg["SPECIAL_REQUESTS"])

    cb = page.locator("input[type='checkbox']").first
    if await cb.count() > 0 and not await cb.is_checked():
        await cb.click()

    log.info("  Form filled")
    await page.wait_for_timeout(1000)


async def step_proceed(page):
    log.info("[7/8] PROCEED...")
    await page.locator("button", has_text="PROCEED").first.click()
    await page.wait_for_timeout(5000)


async def step_payment(page):
    """
    Handle Razorpay payment gateway.
    Strategy: Wallet > Amazon Pay (auto-debit if balance sufficient).
    Fallback: capture the payment URL for manual completion.
    """
    log.info("[8/8] Payment gateway (Razorpay)...")

    # Wait for Razorpay iframe/modal to load
    # Razorpay opens in an iframe with class 'razorpay-checkout-frame'
    razorpay_frame = None
    try:
        # Check if payment is in an iframe
        frame_loc = page.frame_locator("iframe[class*='razorpay'], iframe[src*='razorpay'], iframe[name*='razorpay']")
        # Test if frame exists by looking for content
        wallet_in_frame = frame_loc.locator("text=Wallet")
        if await wallet_in_frame.count() > 0:
            razorpay_frame = frame_loc
            log.info("  Razorpay iframe detected")
    except Exception:
        pass

    # Use frame context or page directly
    ctx = razorpay_frame if razorpay_frame else page

    try:
        # Step A: Click "Wallet" in payment method sidebar
        wallet_loc = ctx.locator("text=Wallet").first
        await wallet_loc.wait_for(timeout=15000)
        await wallet_loc.click()
        log.info("  Selected: Wallet")
        await page.wait_for_timeout(2000)

        # Step B: Click "Amazon Pay"
        amazon_loc = ctx.locator("text=Amazon Pay").first
        await amazon_loc.wait_for(timeout=5000)
        await amazon_loc.click()
        log.info("  Selected: Amazon Pay")
        await page.wait_for_timeout(2000)

        # Step C: Click "Pay" / "Pay Now" button if present (Razorpay confirm)
        pay_btn = ctx.locator("button:has-text('Pay'), button[id*='pay']").first
        if await pay_btn.count() > 0:
            await pay_btn.click()
            log.info("  Clicked Pay - processing...")
            await page.wait_for_timeout(5000)

        # Check for OTP or redirect
        # Amazon Pay may ask for OTP - we can't automate that
        # Check if we're on a success page or need manual intervention
        current_url = page.url
        log.info(f"  Current URL: {current_url}")

        # If Amazon Pay redirects for auth, capture the URL
        if "amazon" in current_url.lower():
            log.info("  +---------------------------------------------+")
            log.info("  | Amazon Pay auth required.                    |")
            log.info("  | Complete OTP/login in the browser window.    |")
            log.info("  +---------------------------------------------+")
            # Wait for user to complete
            await page.wait_for_timeout(60000)
            return

        # Check for success indicators
        success = page.locator("text=/success|confirmed|booked/i").first
        if await success.count() > 0:
            log.info("  Payment successful!")
            return

        log.info("  Payment initiated. Waiting for completion...")
        await page.wait_for_timeout(30000)

    except Exception as e:
        log.warning(f"  Auto-payment failed: {e}")
        log.info("  Attempting fallback...")

        # Fallback: try UPI or capture payment link
        try:
            # Try to find any "Pay" button directly
            any_pay = ctx.locator("button:has-text('Pay')").first
            if await any_pay.count() > 0:
                await any_pay.click()
                log.info("  Clicked generic Pay button")
                await page.wait_for_timeout(5000)
        except Exception:
            pass

        # Capture current URL for manual payment
        current_url = page.url
        log.info("  +---------------------------------------------+")
        log.info("  | MANUAL PAYMENT REQUIRED                     |")
        log.info(f"  | URL: {current_url[:50]}...")
        log.info("  | Complete payment in the browser window.      |")
        log.info("  | Browser will stay open for 2 minutes.        |")
        log.info("  +---------------------------------------------+")

        # Take screenshot of payment page
        await page.screenshot(path="logs/payment_page.png")
        log.info("  Screenshot: logs/payment_page.png")

        # Keep browser open for manual payment
        await page.wait_for_timeout(120000)


# ================================================================
# ENTRY POINT
# ================================================================

if __name__ == "__main__":
    cfg = collect_config()
    asyncio.run(run_bot(cfg))
