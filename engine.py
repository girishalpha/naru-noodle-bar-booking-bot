"""
Naru Booking Engine - Core automation logic.
Uses Playwright Firefox with stealth configuration.
Shared between CLI bot and MCP server.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
from playwright.async_api import async_playwright, Page, BrowserContext, expect

log = logging.getLogger("naru.engine")

BOOKING_URL = "https://bookings.airmenus.in/CafeAir/CafeAir/"
SLOT_MAP = {
    "12:30": "12:30 PM", "14:30": "02:30 PM", "18:30": "06:30 PM", "20:30": "08:30 PM",
    "19:00": "07:00 PM", "21:30": "09:30 PM", "13:00": "01:00 PM", "19:30": "07:30 PM",
    "20:00": "08:00 PM", "21:00": "09:00 PM",
}

# Seating options - maps short config names to card title text on the site
SEATING_MAP = {
    "TABLE2": "Table for 2",
    "TABLE3": "Table for 3",
    "SOFA": "Sofa seating",
    "COMMUNITY": "Community Seating",
    "DINNER": "dinner",
}
VALID_SEATING = list(SEATING_MAP.keys())


@dataclass
class BookingConfig:
    name: str
    email: str
    phone: str
    slot: str = "19:00"
    seating: str = "TABLE2"
    guests: int = 2
    target_date: str = ""
    special_requests: str = ""
    headless: bool = False
    booking_url: str = BOOKING_URL

    def __post_init__(self):
        self.seating = self.seating.upper()
        if not self.target_date:
            self.target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")


@dataclass
class BookingResult:
    status: str  # success, partial, failed, error
    message: str
    payment_url: str = ""
    screenshot: str = ""

    def to_dict(self) -> dict:
        d = {"status": self.status, "message": self.message}
        if self.payment_url:
            d["payment_url"] = self.payment_url
        if self.screenshot:
            d["screenshot"] = self.screenshot
        return d


def slot_to_display(slot_24h: str) -> str:
    """Convert 24h slot (e.g. '19:00') to display format (e.g. '07:00 PM')."""
    if slot_24h in SLOT_MAP:
        return SLOT_MAP[slot_24h]
    # Dynamic conversion for any HH:MM format
    try:
        h, m = map(int, slot_24h.split(":"))
        period = "AM" if h < 12 else "PM"
        h12 = h if h <= 12 else h - 12
        if h12 == 0:
            h12 = 12
        return f"{h12:02d}:{m:02d} {period}"
    except (ValueError, AttributeError):
        return slot_24h


def validate_config(cfg: BookingConfig) -> Optional[str]:
    import re
    if not re.match(r"^\d{1,2}:\d{2}$", cfg.slot):
        return f"Invalid slot format '{cfg.slot}'. Use HH:MM (e.g. 19:00, 20:30)"
    if not cfg.phone.isdigit() or len(cfg.phone) != 10:
        return "Phone must be exactly 10 digits (no +91 prefix)"
    if cfg.seating not in VALID_SEATING:
        return f"Seating must be one of: {', '.join(VALID_SEATING)}"
    if cfg.guests < 1 or cfg.guests > 5:
        return "Guests must be between 1 and 5"
    if "@" not in cfg.email:
        return "Invalid email address"
    return None


async def run_booking(cfg: BookingConfig, max_retries: int = 3) -> BookingResult:
    """Execute the full booking flow with retries."""
    error = validate_config(cfg)
    if error:
        return BookingResult(status="error", message=error)

    os.makedirs("logs", exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.firefox.launch(
            headless=cfg.headless,
            firefox_user_prefs={
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
                "media.navigator.enabled": False,
            },
        )
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        page = await context.new_page()

        # Remove webdriver flag
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        result = None
        for attempt in range(1, max_retries + 1):
            try:
                log.info(f"=== Attempt {attempt}/{max_retries} ===")
                result = await _execute_flow(page, cfg)
                break
            except Exception as e:
                screenshot_path = f"logs/error_attempt_{attempt}.png"
                await page.screenshot(path=screenshot_path)
                log.error(f"Attempt {attempt} failed: {e}")
                log.info(f"Screenshot: {screenshot_path}")

                if attempt < max_retries:
                    log.info("Retrying in 3s...")
                    await asyncio.sleep(3)
                    await page.goto(cfg.booking_url, wait_until="domcontentloaded")
                    await asyncio.sleep(2)
                else:
                    result = BookingResult(
                        status="failed",
                        message=f"All {max_retries} attempts failed. Last error: {e}",
                        screenshot=screenshot_path,
                    )

        # Keep browser open for manual payment if not headless
        if result and result.status == "partial" and not cfg.headless:
            log.info("Browser staying open for manual payment (2 min)...")
            await asyncio.sleep(120)

        await browser.close()
        return result


async def _execute_flow(page: Page, cfg: BookingConfig) -> BookingResult:
    """Single attempt at the full booking flow."""
    await page.goto(cfg.booking_url, wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(2)

    await _step_date(page, cfg)
    await _step_seating(page, cfg)
    await _step_time_slot(page, cfg)
    await _step_guests(page, cfg)
    await _step_continue(page)
    await _step_form(page, cfg)
    await _step_proceed(page)
    return await _step_payment(page, cfg)


async def _step_date(page: Page, cfg: BookingConfig):
    """Step 1: Select the target date from the calendar."""
    log.info("[1/8] Selecting date...")
    day = str(datetime.strptime(cfg.target_date, "%Y-%m-%d").day)

    await page.evaluate("window.scrollBy(0, 300)")
    await asyncio.sleep(1)

    # Find all buttons and match by exact text content
    buttons = await page.locator("button").all()
    for btn in buttons:
        text = (await btn.text_content() or "").strip()
        if text == day and await btn.is_visible():
            await btn.click()
            log.info(f"  Selected day: {day}")
            await asyncio.sleep(1.5)
            return

    raise Exception(f"Day '{day}' not found in calendar. The date may not be available yet.")


async def _step_seating(page: Page, cfg: BookingConfig):
    """Step 2: Select seating type from GroupCards."""
    target_title = SEATING_MAP.get(cfg.seating, "Table for 2")
    log.info(f"[2/8] Selecting seating: {target_title}...")

    await page.evaluate("window.scrollBy(0, 400)")
    await asyncio.sleep(1)

    # GroupCards use class "GroupCards_group_wrpr__*" with a title element inside
    cards = page.locator("[class*='GroupCards_group_wrpr'], [class*='group_wrpr']")
    count = await cards.count()

    if count > 0:
        for i in range(count):
            card = cards.nth(i)
            title_el = card.locator("[class*='title']").first
            title_text = (await title_el.inner_text() or "").strip() if await title_el.count() > 0 else ""
            if target_title.lower() in title_text.lower():
                book_btn = card.locator("button", has_text="BOOK").first
                if await book_btn.count() > 0:
                    await book_btn.click()
                    log.info(f"  Clicked BOOK on '{title_text}' card")
                    await asyncio.sleep(4)
                    return

    # Fallback: click first available BOOK button
    book_btn = page.locator("button", has_text="BOOK").first
    await book_btn.wait_for(state="visible", timeout=10000)
    await book_btn.click()
    log.info("  Clicked first available BOOK button (fallback)")
    await asyncio.sleep(4)


async def _step_time_slot(page: Page, cfg: BookingConfig):
    """Step 3: Select the time slot."""
    slot_text = slot_to_display(cfg.slot)
    log.info(f"[3/8] Selecting time slot: {slot_text}...")

    # Wait for slot elements to render (they load async after BOOK click)
    await asyncio.sleep(2)

    # Site structure: <p class="Slots_time_box__hAnID"><span>07:00 PM</span><span class="Slots_pax_left__*">3 LEFT</span></p>
    time_boxes = page.locator("[class*='Slots_time_box']")

    # Wait up to 10s for at least one time box to appear
    try:
        await time_boxes.first.wait_for(state="visible", timeout=10000)
    except Exception:
        pass

    count = await time_boxes.count()

    if count > 0:
        # Try to find the preferred slot
        for i in range(count):
            box = time_boxes.nth(i)
            text = (await box.inner_text() or "").strip()
            if slot_text.lower() in text.lower():
                await box.click()
                log.info(f"  Selected: {slot_text}")
                await asyncio.sleep(1)
                return

        # Preferred slot not found, click the first available
        await time_boxes.first.click()
        actual = (await time_boxes.first.inner_text() or "").strip().split("\n")[0]
        log.warning(f"  Preferred slot '{slot_text}' unavailable, picked: {actual}")
        await asyncio.sleep(1)
        return

    # Fallback: regex match on any PM time text
    any_slot = page.locator("text=/\\d+:\\d+\\s*PM/i").first
    if await any_slot.count() > 0:
        await any_slot.click()
        log.warning("  Used fallback PM slot selector")
        await asyncio.sleep(1)
        return

    raise Exception("No time slots available for selection")


async def _step_guests(page: Page, cfg: BookingConfig):
    """Step 4: Set guest count using the +/- buttons (Ant Design icons)."""
    log.info(f"[4/8] Setting guests: {cfg.guests}...")

    # Structure: <button class="Slots_action_btns__*"><span aria-label="minus">...</span></button>
    #            <span class="Slots_count__*">0</span>
    #            <button class="Slots_action_btns__*"><span aria-label="plus">...</span></button>
    plus_btn = page.locator("[class*='Slots_action_btns']:has([aria-label='plus'])").first
    await plus_btn.wait_for(state="visible", timeout=8000)

    for i in range(cfg.guests):
        await plus_btn.click()
        await asyncio.sleep(0.3)

    # Verify count
    count_el = page.locator("[class*='Slots_count__']").first
    if await count_el.count() > 0:
        actual = (await count_el.inner_text() or "").strip()
        log.info(f"  Guests set to {actual}")
    else:
        log.info(f"  Clicked + {cfg.guests} times")
    await asyncio.sleep(0.5)


async def _step_continue(page: Page):
    """Step 5: Click CONTINUE button."""
    log.info("[5/8] Clicking CONTINUE...")
    # Button has class Slots_continue_btn__*
    btn = page.locator("[class*='Slots_continue_btn'], button:has-text('CONTINUE')").first
    await btn.wait_for(state="visible", timeout=10000)
    await btn.click()
    await asyncio.sleep(3)
    log.info("  Done")


async def _step_form(page: Page, cfg: BookingConfig):
    """Step 6: Fill the booking form (name, email, phone, T&C)."""
    log.info("[6/8] Filling form...")
    await asyncio.sleep(2)

    # Target fields by their name attribute to avoid honeypot fields
    # Real fields: name="name", name="email", name="mobile"
    # Honeypots: random gibberish names like "jktytsxix", invisible

    # Name field
    name_field = page.locator("input[name='name']")
    await name_field.wait_for(state="visible", timeout=10000)
    await name_field.fill(cfg.name)

    # Email field
    email_field = page.locator("input[name='email']")
    await email_field.wait_for(state="visible", timeout=10000)
    await email_field.fill(cfg.email)

    # Phone field
    phone_field = page.locator("input[name='mobile']")
    await phone_field.wait_for(state="visible", timeout=10000)
    await phone_field.fill(cfg.phone)

    # Special requests (optional)
    if cfg.special_requests:
        textarea = page.locator("textarea").first
        if await textarea.count() > 0:
            await textarea.fill(cfg.special_requests)

    # Terms & conditions checkbox
    checkbox = page.locator("input[type='checkbox']").first
    if await checkbox.count() > 0 and not await checkbox.is_checked():
        await checkbox.click()

    log.info("  Form filled")
    await asyncio.sleep(1)


async def _step_proceed(page: Page):
    """Step 7: Click PROCEED to go to payment."""
    log.info("[7/8] Clicking PROCEED...")
    btn = page.locator("button", has_text="PROCEED").first
    await btn.wait_for(state="visible", timeout=10000)
    await btn.click()
    await asyncio.sleep(5)
    log.info("  Done")


async def _step_payment(page: Page, cfg: BookingConfig) -> BookingResult:
    """Step 8: Handle Razorpay payment gateway.

    Strategy: dismiss contact overlay, then try payment methods in order:
    1. Wallet > Amazon Pay
    2. UPI (if wallet fails)
    3. Any available Pay button

    Since all methods require OTP/auth, the goal is to get as far as possible
    and return the payment URL for manual completion if needed.
    """
    log.info("[8/8] Payment (Razorpay)...")

    # Detect Razorpay iframe
    ctx = page
    try:
        frame = page.frame_locator("iframe[class*='razorpay'], iframe[src*='razorpay'], iframe[name*='razorpay']")
        test = frame.locator("body")
        if await test.count() > 0:
            ctx = frame
            log.info("  Razorpay iframe detected")
    except Exception:
        pass

    try:
        # Dismiss contact overlay (phone/email verification screen)
        await _dismiss_razorpay_contact_overlay(ctx, cfg)

        # Try payment methods in priority order
        payment_selected = await _try_select_payment_method(ctx)

        if payment_selected:
            # Click Pay/Submit button
            await asyncio.sleep(2)
            pay_btn = ctx.locator("button:has-text('Pay')").first
            if await pay_btn.count() > 0 and await pay_btn.is_visible():
                await pay_btn.click()
                log.info("  Pay button clicked")
                await asyncio.sleep(5)

        current_url = page.url

        # Check for redirect (Amazon, UPI app, etc.)
        if "amazon" in current_url.lower() or "upi" in current_url.lower():
            log.info("  Redirected to payment provider for auth")
            return BookingResult(
                status="partial",
                message="Booking submitted. Complete payment authentication in browser.",
                payment_url=current_url,
            )

        # Check for success
        success = page.locator("text=/success|confirmed|booked/i").first
        if await success.count() > 0:
            log.info("  Payment successful!")
            return BookingResult(status="success", message="Booking confirmed and payment completed!")

        # Booking is submitted, payment gateway is open
        screenshot_path = "logs/payment_stage.png"
        await page.screenshot(path=screenshot_path)
        return BookingResult(
            status="partial",
            message="Booking submitted. Razorpay payment gateway is open - complete payment manually.",
            payment_url=current_url,
            screenshot=screenshot_path,
        )

    except Exception as e:
        current_url = page.url
        screenshot_path = "logs/payment_stage.png"
        await page.screenshot(path=screenshot_path)
        log.warning(f"  Payment automation failed: {e}")
        return BookingResult(
            status="partial",
            message=f"Booking submitted. Complete payment manually.",
            payment_url=current_url,
            screenshot=screenshot_path,
        )


async def _try_select_payment_method(ctx) -> bool:
    """Try to select a payment method in Razorpay. Returns True if one was selected."""

    # Strategy 1: Wallet > Amazon Pay
    try:
        wallet = ctx.locator("[data-testid='Wallet']").first
        if await wallet.count() > 0 and await wallet.is_visible():
            await wallet.click(force=True)
            log.info("  Selected: Wallet")
            await asyncio.sleep(2)

            amazon = ctx.locator("text=Amazon Pay").first
            if await amazon.count() > 0 and await amazon.is_visible():
                await amazon.click()
                log.info("  Selected: Amazon Pay")
                return True
            else:
                # Pick first available wallet option
                wallet_option = ctx.locator("[data-testid='wallet-option'], .wallet-option, [role='radio']").first
                if await wallet_option.count() > 0 and await wallet_option.is_visible():
                    await wallet_option.click()
                    log.info("  Selected: first available wallet")
                    return True
    except Exception:
        pass

    # Strategy 2: UPI
    try:
        upi = ctx.locator("[data-testid='UPI'], text=UPI").first
        if await upi.count() > 0 and await upi.is_visible():
            await upi.click(force=True)
            log.info("  Selected: UPI")
            await asyncio.sleep(1)
            return True
    except Exception:
        pass

    # Strategy 3: Click any visible payment method tab
    try:
        methods = ctx.locator("[data-testid*='method'], [role='tab']").all()
        for method in await methods:
            if await method.is_visible():
                text = (await method.text_content() or "").strip()
                await method.click(force=True)
                log.info(f"  Selected payment method: {text}")
                return True
    except Exception:
        pass

    log.warning("  Could not auto-select a payment method")
    return False


async def _dismiss_razorpay_contact_overlay(ctx, cfg: BookingConfig):
    """Dismiss the Razorpay contact overlay that blocks payment method selection.

    Razorpay shows a phone/email verification overlay before showing payment options.
    We fill in the contact details and submit to dismiss it.
    """
    overlay = ctx.locator("[data-testid='contact-overlay-container']").first
    try:
        await overlay.wait_for(timeout=8000)
    except Exception:
        # No overlay present, payment methods are directly visible
        log.info("  No contact overlay detected, proceeding directly")
        return

    log.info("  Dismissing Razorpay contact overlay...")

    # Fill phone number using data-testid
    phone_input = ctx.locator("[data-testid='contactNumber']").first
    if await phone_input.count() > 0:
        await phone_input.fill(cfg.phone)
        log.info("  Filled phone in Razorpay overlay")
        await asyncio.sleep(0.5)

    # Fill email using data-testid
    email_input = ctx.locator("[data-testid='email']").first
    if await email_input.count() > 0:
        await email_input.fill(cfg.email)
        log.info("  Filled email in Razorpay overlay")
        await asyncio.sleep(0.5)

    # Click the visible "Continue" button in the overlay (has class bg-cta)
    continue_btn = overlay.locator("button:has-text('Continue')").first
    if await continue_btn.count() > 0 and await continue_btn.is_visible():
        await continue_btn.click()
        log.info("  Clicked Continue on contact overlay")
        await asyncio.sleep(4)
    else:
        # Fallback: press Enter on the last input
        await email_input.press("Enter")
        log.info("  Submitted overlay via Enter key")
        await asyncio.sleep(4)

    # Wait for overlay to disappear
    try:
        await overlay.wait_for(state="hidden", timeout=10000)
        log.info("  Contact overlay dismissed")
    except Exception:
        log.warning("  Overlay may still be visible, proceeding anyway")
