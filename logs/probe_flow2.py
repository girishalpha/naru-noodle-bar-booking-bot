"""Probe time slot DOM structure after BOOK click."""
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
                print(f"Clicked day: {day}")
                break
        await asyncio.sleep(2)
        
        # Click BOOK
        book_btn = page.locator("button", has_text="BOOK").first
        await book_btn.click()
        print("Clicked BOOK")
        await asyncio.sleep(4)
        
        # Get visible text (safely)
        visible_text = await page.evaluate("() => document.body.innerText.substring(0, 3000)")
        print("\n=== VISIBLE TEXT ===")
        print(visible_text)
        
        # Get all classes present now
        print("\n=== RELEVANT CLASSES ===")
        classes = await page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('*').forEach(el => {
                if (el.className && typeof el.className === 'string') {
                    const cls = el.className;
                    if (/slot|time|guest|book|select|card|group|step/i.test(cls)) {
                        const text = (el.textContent || '').trim().substring(0, 60);
                        results.push({tag: el.tagName, cls: cls.substring(0, 100), text: text});
                    }
                }
            });
            return results.slice(0, 40);
        }""")
        for el in classes:
            print(f"  <{el['tag']}> class='{el['cls']}' text='{el['text']}'")
        
        # Specifically look for elements with PM/AM time text
        print("\n=== ELEMENTS WITH TIME TEXT ===")
        time_els = await page.evaluate("""() => {
            const results = [];
            const all = document.querySelectorAll('*');
            for (const el of all) {
                const directText = Array.from(el.childNodes)
                    .filter(n => n.nodeType === 3)
                    .map(n => n.textContent.trim())
                    .join('');
                const innerText = (el.textContent || '').trim();
                if (/\d{1,2}:\d{2}\s*(AM|PM)/i.test(innerText) && innerText.length < 80) {
                    results.push({
                        tag: el.tagName,
                        cls: (el.className || '').substring(0, 100),
                        text: innerText.substring(0, 60),
                        directText: directText.substring(0, 40),
                        children: el.children.length,
                        clickable: el.tagName === 'BUTTON' || el.onclick !== null || el.getAttribute('role') === 'button'
                    });
                }
            }
            return results.slice(0, 30);
        }""")
        for el in time_els:
            print(f"  <{el['tag']}> class='{el['cls']}' direct='{el['directText']}' full='{el['text']}' children={el['children']} clickable={el['clickable']}")
        
        # Get the HTML around time slots
        print("\n=== HTML SNIPPET AROUND SLOTS ===")
        slot_html = await page.evaluate("""() => {
            const els = document.querySelectorAll('*');
            for (const el of els) {
                if (/\d{1,2}:\d{2}\s*(AM|PM)/i.test(el.textContent || '') && el.children.length > 1 && el.children.length < 20) {
                    // This is likely the container
                    if (el.className && /slot|time|select/i.test(el.className)) {
                        return el.outerHTML.substring(0, 2000);
                    }
                }
            }
            // Fallback: find first element with PM text that has siblings
            for (const el of els) {
                const text = (el.textContent || '').trim();
                if (/^\d{1,2}:\d{2}\s*(AM|PM)$/i.test(text)) {
                    return el.parentElement.outerHTML.substring(0, 2000);
                }
            }
            return 'NOT FOUND';
        }""")
        print(slot_html)
        
        await page.screenshot(path="logs/step2_slots.png")
        await browser.close()

asyncio.run(probe())
