from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
import time
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('booking_bot.log'),
        logging.StreamHandler()
    ]
)

load_dotenv()


class EatNaruBookingBot:
    def __init__(self):
        self.url = os.getenv('BOOKING_URL')
        self.name = os.getenv('USER_NAME')
        self.email = os.getenv('USER_EMAIL')
        self.phone = os.getenv('USER_PHONE')
        self.guests = int(os.getenv('GUESTS', 2))
        self.seating_preference = os.getenv('SEATING_PREFERENCE', '')
        self.slot_preference = os.getenv('SLOT_PREFERENCE', '14:30')
        self.date_offset = int(os.getenv('DATE_OFFSET_DAYS', 1))

        self._validate()
        self._setup_driver()

    def _validate(self):
        required = ['USER_NAME', 'USER_EMAIL', 'USER_PHONE', 'BOOKING_URL']
        missing = [v for v in required if not os.getenv(v)]
        if missing:
            raise ValueError(f"Missing env vars: {', '.join(missing)}")
        if '@' not in self.email:
            raise ValueError("Invalid email format")
        if not self.phone.isdigit() or len(self.phone) != 10:
            raise ValueError("Phone must be 10 digits")

    def _setup_driver(self):
        opts = Options()
        opts.add_argument('--start-maximized')
        opts.add_argument('--disable-popup-blocking')
        headless = os.getenv('HEADLESS', 'false').lower() == 'true'
        if headless:
            opts.add_argument('--headless=new')
        self.driver = webdriver.Chrome(options=opts)
        logging.info("Chrome started (headless=%s)", headless)

    def _wait(self, by, value, timeout=10, clickable=False):
        cond = EC.element_to_be_clickable if clickable else EC.presence_of_element_located
        return WebDriverWait(self.driver, timeout).until(cond((by, value)))

    def _select_date(self):
        time.sleep(2)
        target_day = str((datetime.now() + timedelta(days=self.date_offset)).day)
        buttons = self.driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if btn.text.strip() == target_day and btn.is_displayed():
                self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                time.sleep(0.3)
                btn.click()
                logging.info("Selected date: day %s", target_day)
                time.sleep(2)
                return
        raise ValueError(f"Day {target_day} button not found")

    def _select_seating(self):
        # Wait for cards to fully render
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='GroupCards_group_wrpr'], [class*='group_wrpr']"))
        )
        time.sleep(1)
        cards = self.driver.find_elements(By.CSS_SELECTOR, "[class*='GroupCards_group_wrpr'], [class*='group_wrpr']")
        logging.info("Found %d seating cards", len(cards))

        for card in cards:
            try:
                title = card.find_element(By.CSS_SELECTOR, "[class*='title']").text.strip()
            except:
                title = ""
            # Match preference or take first card if no preference set
            if not self.seating_preference or self.seating_preference.lower() in title.lower():
                # Try class-based selector first, then text-based
                try:
                    book_btn = card.find_element(By.CSS_SELECTOR, "button[class*='book'], button[class*='Book']")
                except:
                    try:
                        book_btn = card.find_element(By.XPATH, ".//button")
                    except:
                        continue
                self.driver.execute_script("arguments[0].scrollIntoView(true);", book_btn)
                time.sleep(0.3)
                book_btn.click()
                logging.info("Selected seating: '%s'", title)
                time.sleep(3)
                return

        # Fallback: any visible button in the cards area
        buttons = self.driver.find_elements(By.CSS_SELECTOR, "[class*='group_wrpr'] button, [class*='GroupCards'] button")
        if buttons:
            buttons[0].click()
            logging.info("Fallback: clicked first card button")
            time.sleep(3)
        else:
            raise ValueError("No BOOK button found in any seating card")

    def _select_time_slot(self):
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='Slots_time_box']"))
        )
        time_boxes = self.driver.find_elements(By.CSS_SELECTOR, "[class*='Slots_time_box']")
        logging.info("Found %d time slots", len(time_boxes))

        for box in time_boxes:
            text = box.text.strip()
            if self.slot_preference.lower() in text.lower():
                box.click()
                logging.info("Selected slot: %s", text)
                time.sleep(1)
                return

        # Fallback: first slot
        if time_boxes:
            time_boxes[0].click()
            logging.info("Preferred slot not found, selected: %s", time_boxes[0].text.strip())
            time.sleep(1)

    def _set_guests(self):
        plus_btns = self.driver.find_elements(By.CSS_SELECTOR, "[class*='Slots_action_btns']")
        if len(plus_btns) >= 2:
            plus_btn = plus_btns[1]  # second button is +
        else:
            plus_btn = plus_btns[-1]

        clicks = self.guests - 1  # starts at 1
        for _ in range(clicks):
            plus_btn.click()
            time.sleep(0.3)

        try:
            count_el = self.driver.find_element(By.CSS_SELECTOR, "[class*='Slots_count']")
            logging.info("Guest count: %s", count_el.text.strip())
        except:
            logging.info("Clicked + %d times for %d guests", clicks, self.guests)

    def _click_continue(self):
        btn = self._wait(By.CSS_SELECTOR, "[class*='Slots_continue_btn']", clickable=True)
        btn.click()
        logging.info("Clicked CONTINUE")
        time.sleep(3)

    def _fill_form(self):
        self._wait(By.CSS_SELECTOR, "input[name='name']")
        self.driver.find_element(By.CSS_SELECTOR, "input[name='name']").send_keys(self.name)
        self.driver.find_element(By.CSS_SELECTOR, "input[name='email']").send_keys(self.email)
        self.driver.find_element(By.CSS_SELECTOR, "input[name='mobile']").send_keys(self.phone)

        special = os.getenv('SPECIAL_REQUESTS', '')
        if special:
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            if textareas:
                textareas[0].send_keys(special)

        checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
        for cb in checkboxes:
            if not cb.is_selected():
                self.driver.execute_script("arguments[0].click();", cb)

        logging.info("Form filled")

    def _click_proceed(self):
        btn = self._wait(By.XPATH, "//button[contains(text(),'PROCEED')]", clickable=True)
        btn.click()
        logging.info("Clicked PROCEED — heading to payment")
        time.sleep(3)

    def run(self):
        try:
            logging.info("Starting booking at %s", self.url)
            self.driver.get(self.url)

            self._select_date()
            self._select_seating()
            self._select_time_slot()
            self._set_guests()
            self._click_continue()
            self._fill_form()
            self._click_proceed()

            logging.info("Reached payment page. Bot stops here.")
            self.driver.save_screenshot("booking_success.png")

        except Exception as e:
            logging.error("Booking failed: %s", e)
            self.driver.save_screenshot("booking_error.png")
            raise
        finally:
            try:
                input("Press Enter to close browser...")
            except EOFError:
                time.sleep(30)
            self.driver.quit()


if __name__ == "__main__":
    bot = EatNaruBookingBot()
    bot.run()
