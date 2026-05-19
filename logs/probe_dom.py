"""Dump DOM after clicking BOOK to find actual time slot structure."""
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
        
        # Click date
        day = str((datetime.now() + timedelta(days=1)).day)
        buttons = await page.locator("button").all()
        for btn in buttons:
            text = (await btn.text_content() or "").strip()
            if text == day and await btn.is_visible():
                await btn.click()
                print(f"Clicked day: {day}")
                break
        await asyncio.sleep(2)
        
        # Click BOOK
        book_btn = page.locator("button", has_text="BOOK").first
        if await book_btn.count() > 0:
            await book_btn.click()
            print("Clicked BOOK")
        await asyncio.sleep(3)
        
        # Dump the full page HTML (trimmed)
        html = await page.content()
        # Save full HTML for inspection
        with open("logs/page_after_book.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Full HTML saved ({len(html)} chars)")
        
        # Look for anything with PM/AM text
        print("\n--- Elements containing time patterns ---")
        time_els = await page.evaluate("""() => {
            const results = [];
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
            while (walker.nextNode()) {
                const el = walker.currentNode;
                const text = el.textContent || '';
                if (/\d{1,2}:\d{2}\s*(AM|PM)/i.test(text) && text.length < 100) {
                    results.push({
                        tag: el.tagName,
                        class: el.className.substring(0, 100),
                        text: text.substring(0, 60),
                        id: el.id,
                        children: el.children.length
                    });
                }
            }
            return results.slice(0, 30);
        }""")
        for el in time_els:
            print(f"  <{el['tag']}> class='{el['class']}' text='{el['text']}' children={el['children']}")
        
        # Also look for what's visible on screen
        print("\n--- Visible clickable elements ---")
        clickable = await page.evaluate("""() => {
            const results = [];
            const els = document.querySelectorAll('button, [role="button"], [onclick], a, div[class*="box"], p[class*="box"], span[class*="slot"], div[class*="slot"]');
            for (const el of els) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0 && rect.top < 1000) {
                    const text = (el.textContent || '').trim().substring(0, 50);
                    if (text && text.length < 50) {
                        results.push({
                            tag: el.tagName,
                            class: el.className.substring(0, 80),
                            text: text,
                            role: el.getAttribute('role') || ''
                        });
                    }
                }
            }
            return results.slice(0, 40);
        }""")
        for el in clickable:
            print(f"  <{el['tag']}> class='{el['class'][:60]}' text='{el['text']}'")
        
        await page.screenshot(path="logs/probe_dom.png")
        await browser.close()

asyncio.run(probe())
