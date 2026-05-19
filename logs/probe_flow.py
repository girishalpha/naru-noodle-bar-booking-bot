"""Probe the full booking flow step by step with screenshots and DOM monitoring."""
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta

BOOKING_URL = "https://bookings.airmenus.in/CafeAir/CafeAir/"

async def probe():
    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(BOOKING_URL, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)
        
        print(f"URL after load: {page.url}")
        await page.screenshot(path="logs/step0_loaded.png")
        
        # Step 1: Click date
        day = str((datetime.now() + timedelta(days=1)).day)
        clicked = False
        buttons = await page.locator("button").all()
        for btn in buttons:
            text = (await btn.text_content() or "").strip()
            if text == day and await btn.is_visible():
                await btn.click()
                clicked = True
                print(f"Step 1: Clicked day {day}")
                break
        if not clicked:
            print(f"Step 1: FAILED - day {day} not found")
            await browser.close()
            return
        
        await asyncio.sleep(2)
        await page.screenshot(path="logs/step1_date.png")
        print(f"URL after date: {page.url}")
        
        # Step 2: Check what's visible now - look for BOOK buttons
        book_btns = page.locator("button", has_text="BOOK")
        book_count = await book_btns.count()
        print(f"Step 2: Found {book_count} BOOK buttons")
        
        if book_count > 0:
            # Print info about each BOOK button
            for i in range(book_count):
                btn = book_btns.nth(i)
                visible = await btn.is_visible()
                parent_text = await btn.evaluate("el => el.closest('[class*=group_wrpr], [class*=GroupCards]')?.textContent?.substring(0, 100) || 'no parent'")
                print(f"  BOOK[{i}]: visible={visible}, context='{parent_text[:80]}'")
            
            # Click first visible BOOK button
            await book_btns.first.click()
            print("Step 2: Clicked first BOOK button")
        
        # Wait longer and monitor for changes
        print("\nWaiting for content to load after BOOK click...")
        for wait in [2, 3, 5, 5]:
            await asyncio.sleep(wait)
            url = page.url
            # Check for new elements
            body_text = await page.evaluate("() => document.body.innerText.substring(0, 2000)")
            has_pm = "PM" in body_text or "pm" in body_text
            has_slot = "slot" in body_text.lower()
            has_guest = "guest" in body_text.lower()
            has_continue = "CONTINUE" in body_text or "Continue" in body_text
            spinner = page.locator("[class*='spinner']")
            spinner_count = await spinner.count()
            print(f"  +{wait}s: url={url[-30:]}, PM={has_pm}, slot={has_slot}, guest={has_guest}, continue={has_continue}, spinners={spinner_count}")
            
            if has_pm or has_guest or has_continue:
                break
        
        await page.screenshot(path="logs/step2_after_book.png")
        
        # Dump visible text
        visible_text = await page.evaluate("() => document.body.innerText")
        print(f"\n--- VISIBLE TEXT (first 3000 chars) ---")
        print(visible_text[:3000])
        
        # Check for any new classes that appeared
        new_classes = await page.evaluate("""() => {
            const classes = new Set();
            document.querySelectorAll('*').forEach(el => {
                if (el.className && typeof el.className === 'string') {
                    el.className.split(' ').forEach(c => { if (c.length > 3) classes.add(c); });
                }
            });
            return [...classes].sort();
        }""")
        print(f"\n--- ALL CLASSES ({len(new_classes)}) ---")
        for c in new_classes:
            if any(k in c.lower() for k in ['slot', 'time', 'guest', 'book', 'form', 'step', 'select', 'card', 'group']):
                print(f"  {c}")
        
        await browser.close()

asyncio.run(probe())
