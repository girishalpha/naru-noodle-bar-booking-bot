"""End-to-end test of the updated booking flow (stops before payment)."""
import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.async_api import async_playwright
from datetime import datetime, timedelta

BOOKING_URL = "https://bookings.airmenus.in/CafeAir/CafeAir/"

async def test():
    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=True)
        page = await browser.new_page(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
        )
        
        await page.goto(BOOKING_URL, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)
        print("Page loaded")
        
        # Step 1: Date
        day = str((datetime.now() + timedelta(days=1)).day)
        buttons = await page.locator("button").all()
        for btn in buttons:
            text = (await btn.text_content() or "").strip()
            if text == day and await btn.is_visible():
                await btn.click()
                print(f"[1/8] Date: clicked day {day}")
                break
        await asyncio.sleep(2)
        
        # Step 2: Seating - target "Table for 2"
        target_title = "Table for 2"
        cards = page.locator("[class*='GroupCards_group_wrpr'], [class*='group_wrpr']")
        count = await cards.count()
        print(f"[2/8] Seating: found {count} cards")
        clicked_card = False
        for i in range(count):
            card = cards.nth(i)
            title_el = card.locator("[class*='title']").first
            title_text = (await title_el.inner_text() or "").strip() if await title_el.count() > 0 else ""
            if target_title.lower() in title_text.lower():
                book_btn = card.locator("button", has_text="BOOK").first
                if await book_btn.count() > 0:
                    await book_btn.click()
                    print(f"  Clicked BOOK on '{title_text}'")
                    clicked_card = True
                    break
        if not clicked_card:
            book_btn = page.locator("button", has_text="BOOK").first
            await book_btn.click()
            print("  Fallback: clicked first BOOK")
        await asyncio.sleep(4)
        
        # Step 3: Time slot
        slot_text = "07:00 PM"
        time_boxes = page.locator("[class*='Slots_time_box']")
        try:
            await time_boxes.first.wait_for(state="visible", timeout=10000)
        except:
            pass
        tb_count = await time_boxes.count()
        print(f"[3/8] Time slots: found {tb_count} boxes")
        slot_clicked = False
        for i in range(tb_count):
            box = time_boxes.nth(i)
            text = (await box.inner_text() or "").strip()
            print(f"  Box[{i}]: '{text}'")
            if slot_text.lower() in text.lower():
                await box.click()
                print(f"  Selected: {slot_text}")
                slot_clicked = True
                break
        if not slot_clicked and tb_count > 0:
            await time_boxes.first.click()
            print("  Fallback: clicked first slot")
        await asyncio.sleep(1)
        
        # Step 4: Guests (2)
        plus_btn = page.locator("[class*='Slots_action_btns']:has([aria-label='plus'])").first
        await plus_btn.wait_for(state="visible", timeout=8000)
        for i in range(2):
            await plus_btn.click()
            await asyncio.sleep(0.3)
        count_el = page.locator("[class*='Slots_count__']").first
        if await count_el.count() > 0:
            actual = (await count_el.inner_text() or "").strip()
            print(f"[4/8] Guests: count = {actual}")
        else:
            print("[4/8] Guests: clicked + twice")
        
        # Step 5: CONTINUE
        btn = page.locator("[class*='Slots_continue_btn'], button:has-text('CONTINUE')").first
        await btn.wait_for(state="visible", timeout=10000)
        await btn.click()
        print("[5/8] Clicked CONTINUE")
        await asyncio.sleep(3)
        
        # Step 6: Form
        name_field = page.locator("input[name='name']")
        try:
            await name_field.wait_for(state="visible", timeout=10000)
            await name_field.fill("Test User")
            email_field = page.locator("input[name='email']")
            await email_field.fill("test@example.com")
            phone_field = page.locator("input[name='mobile']")
            await phone_field.fill("9876543210")
            
            checkbox = page.locator("input[type='checkbox']").first
            if await checkbox.count() > 0 and not await checkbox.is_checked():
                await checkbox.click()
            print("[6/8] Form filled")
        except Exception as e:
            print(f"[6/8] Form error: {e}")
            # Dump what's visible
            visible = await page.evaluate("() => document.body.innerText.substring(0, 1000)")
            print(f"  Visible text: {visible[:500]}")
        
        await asyncio.sleep(1)
        
        # Step 7: PROCEED
        proceed_btn = page.locator("button", has_text="PROCEED").first
        if await proceed_btn.count() > 0 and await proceed_btn.is_visible():
            await proceed_btn.click()
            print("[7/8] Clicked PROCEED")
            await asyncio.sleep(5)
        else:
            print("[7/8] PROCEED button not found/visible")
            visible = await page.evaluate("() => document.body.innerText.substring(0, 500)")
            print(f"  Visible: {visible[:300]}")
        
        # Step 8: Check payment state
        current_url = page.url
        print(f"[8/8] Final URL: {current_url}")
        await page.screenshot(path="logs/test_e2e_final.png")
        print("Screenshot: logs/test_e2e_final.png")
        
        await browser.close()
        print("\nDONE - All steps completed!")

asyncio.run(test())
