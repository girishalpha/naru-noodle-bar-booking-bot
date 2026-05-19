"""Quick probe: verify time slot selectors work on the live site."""
import asyncio
from playwright.async_api import async_playwright

BOOKING_URL = "https://bookings.airmenus.in/CafeAir/CafeAir/"

async def probe():
    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=True)
        page = await browser.new_page()
        
        print("Navigating to booking page...")
        await page.goto(BOOKING_URL, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)
        
        # Step 1: Click a date (tomorrow)
        from datetime import datetime, timedelta
        day = str((datetime.now() + timedelta(days=1)).day)
        buttons = await page.locator("button").all()
        for btn in buttons:
            text = (await btn.text_content() or "").strip()
            if text == day and await btn.is_visible():
                await btn.click()
                print(f"Clicked day: {day}")
                break
        await asyncio.sleep(2)
        
        # Step 2: Click first BOOK button (seating)
        book_btn = page.locator("button", has_text="BOOK").first
        if await book_btn.count() > 0:
            await book_btn.click()
            print("Clicked BOOK button")
        await asyncio.sleep(2)
        
        # Step 3: Probe time slot selectors
        print("\n--- TIME SLOT PROBE ---")
        
        # Test class-based selector
        time_boxes = page.locator("[class*='Slots_time_box'], [class*='time_box'], [class*='time-box']")
        count = await time_boxes.count()
        print(f"Class-based selector found: {count} elements")
        
        if count > 0:
            for i in range(min(count, 10)):
                box = time_boxes.nth(i)
                text = (await box.inner_text() or "").strip()
                tag = await box.evaluate("el => el.tagName")
                classes = await box.evaluate("el => el.className")
                print(f"  [{i}] <{tag}> class='{classes[:60]}' text='{text[:40]}'")
        
        # Also check what's in the DOM around slots
        print("\n--- ALL ELEMENTS WITH 'slot' IN CLASS ---")
        slot_els = page.locator("[class*='Slot']")
        slot_count = await slot_els.count()
        print(f"Found {slot_count} elements with 'Slot' in class")
        for i in range(min(slot_count, 15)):
            el = slot_els.nth(i)
            tag = await el.evaluate("el => el.tagName")
            classes = await el.evaluate("el => el.className")
            text = (await el.inner_text() or "").strip()[:50]
            print(f"  [{i}] <{tag}> class='{classes[:80]}' text='{text}'")
        
        # Fallback: check PM text pattern
        print("\n--- PM TEXT PATTERN ---")
        pm_els = page.locator("text=/\d+:\d+\s*PM/i")
        pm_count = await pm_els.count()
        print(f"PM text pattern found: {pm_count} elements")
        for i in range(min(pm_count, 10)):
            el = pm_els.nth(i)
            text = (await el.inner_text() or "").strip()[:40]
            print(f"  [{i}] '{text}'")
        
        await page.screenshot(path="logs/probe_slots.png")
        print("\nScreenshot saved to logs/probe_slots.png")
        await browser.close()

asyncio.run(probe())
