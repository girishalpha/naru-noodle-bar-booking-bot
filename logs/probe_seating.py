"""Probe seating cards and guest buttons."""
import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
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
        
        # Click date
        day = str((datetime.now() + timedelta(days=1)).day)
        buttons = await page.locator("button").all()
        for btn in buttons:
            text = (await btn.text_content() or "").strip()
            if text == day and await btn.is_visible():
                await btn.click()
                break
        await asyncio.sleep(2)
        
        # Probe GroupCards (seating options)
        print("=== SEATING CARDS (GroupCards) ===")
        cards = await page.evaluate("""() => {
            const results = [];
            const wrappers = document.querySelectorAll('[class*="GroupCards_group_wrpr"], [class*="group_wrpr"]');
            for (const w of wrappers) {
                const title = w.querySelector('[class*="title"]')?.textContent || '';
                const desc = w.querySelector('[class*="description"]')?.textContent || '';
                const remaining = w.querySelector('[class*="remaining"]')?.textContent || '';
                const bookBtn = w.querySelector('[class*="book"]');
                results.push({
                    title: title.trim().substring(0, 80),
                    desc: desc.trim().substring(0, 120),
                    remaining: remaining.trim(),
                    hasBookBtn: !!bookBtn,
                    bookBtnText: bookBtn?.textContent?.trim() || '',
                    fullText: w.textContent.trim().substring(0, 200)
                });
            }
            return results;
        }""")
        for i, card in enumerate(cards):
            print(f"\n  Card [{i}]:")
            print(f"    title: '{card['title']}'")
            print(f"    desc: '{card['desc']}'")
            print(f"    remaining: '{card['remaining']}'")
            print(f"    bookBtn: {card['hasBookBtn']} text='{card['bookBtnText']}'")
            print(f"    fullText: '{card['fullText'][:150]}'")
        
        # Now click BOOK and probe guest buttons
        book_btn = page.locator("button", has_text="BOOK").first
        await book_btn.click()
        await asyncio.sleep(4)
        
        print("\n\n=== GUEST COUNTER BUTTONS ===")
        guest_info = await page.evaluate("""() => {
            const btns = document.querySelectorAll('[class*="Slots_action_btns"]');
            const results = [];
            for (const btn of btns) {
                const svg = btn.querySelector('svg');
                const svgPath = svg?.querySelector('path')?.getAttribute('d')?.substring(0, 30) || '';
                const ariaLabel = btn.getAttribute('aria-label') || '';
                const innerHTML = btn.innerHTML.substring(0, 200);
                const rect = btn.getBoundingClientRect();
                results.push({
                    ariaLabel,
                    hasSvg: !!svg,
                    svgPathStart: svgPath,
                    innerHTML: innerHTML,
                    x: rect.x,
                    y: rect.y
                });
            }
            // Also get the count element
            const count = document.querySelector('[class*="Slots_count"]');
            return {
                buttons: results,
                countText: count?.textContent || 'not found',
                countClass: count?.className || ''
            };
        }""")
        print(f"  Count display: '{guest_info['countText']}' class='{guest_info['countClass']}'")
        for i, btn in enumerate(guest_info['buttons']):
            print(f"  Button [{i}]: aria='{btn['ariaLabel']}' svg={btn['hasSvg']} x={btn['x']:.0f} innerHTML='{btn['innerHTML'][:100]}'")
        
        # Try clicking the second button (likely +) and check count
        action_btns = page.locator("[class*='Slots_action_btns']")
        btn_count = await action_btns.count()
        print(f"\n  Total action buttons: {btn_count}")
        
        if btn_count >= 2:
            # Click second button (likely +)
            await action_btns.nth(1).click()
            await asyncio.sleep(0.5)
            new_count = await page.locator("[class*='Slots_count']").first.inner_text()
            print(f"  After clicking button[1]: count = '{new_count}'")
            
            # Click again
            await action_btns.nth(1).click()
            await asyncio.sleep(0.5)
            new_count2 = await page.locator("[class*='Slots_count']").first.inner_text()
            print(f"  After clicking button[1] again: count = '{new_count2}'")
            
            # Click first button (likely -)
            await action_btns.nth(0).click()
            await asyncio.sleep(0.5)
            new_count3 = await page.locator("[class*='Slots_count']").first.inner_text()
            print(f"  After clicking button[0]: count = '{new_count3}'")
        
        await browser.close()

asyncio.run(probe())
