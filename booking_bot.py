from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta
import time
import schedule
import os
from dotenv import load_dotenv
import logging
import traceback

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('booking_bot.log'),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

class EatNaruBookingBot:
    def __init__(self):
        self.url = os.getenv('BOOKING_URL')
        self.name = os.getenv('USER_NAME')
        self.email = os.getenv('USER_EMAIL')
        self.phone = os.getenv('USER_PHONE')
        self.guests = int(os.getenv('GUESTS', 1))
        self.seating_preference = os.getenv('SEATING_PREFERENCE', 'RAMEN')
        
        # Validate environment variables
        self.validate_env_variables()
        self.setup_driver()

    def validate_env_variables(self):
        required_vars = ['USER_NAME', 'USER_EMAIL', 'USER_PHONE', 'BOOKING_URL', 'MEAL_PREFERENCE', 'SLOT_PREFERENCE']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logging.error(error_msg)
            raise ValueError(error_msg)

        # Validate meal preference
        meal_pref = os.getenv('MEAL_PREFERENCE').upper()
        if meal_pref not in ['LUNCH', 'DINNER']:
            raise ValueError("MEAL_PREFERENCE must be either LUNCH or DINNER")

        # Validate slot preference
        slot_pref = os.getenv('SLOT_PREFERENCE')
        valid_slots = {'12:30', '14:30', '18:30', '20:30'}
        if slot_pref not in valid_slots:
            raise ValueError(f"SLOT_PREFERENCE must be one of: {', '.join(valid_slots)}")

        # Validate email format
        if '@' not in self.email:
            raise ValueError("Invalid email format in environment variables")

        # Validate phone number
        if not self.phone.isdigit() or len(self.phone) != 10:
            raise ValueError("Invalid phone number format in environment variables")

    def setup_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_argument('--disable-popup-blocking')
            
            # Seleniumwire specific options
            seleniumwire_options = {
                'verify_ssl': False,  # Don't verify SSL certificates
                'suppress_connection_errors': False
            }
            
            self.driver = webdriver.Chrome(
                options=chrome_options,
                seleniumwire_options=seleniumwire_options
            )
            logging.info("Browser setup completed successfully")
        except Exception as e:
            logging.error(f"Failed to setup browser: {str(e)}")
            logging.error(f"Detailed error: {traceback.format_exc()}")
            raise

    def wait_for_element(self, by, value, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def select_date(self):
        try:
            # Wait for initial page load
            time.sleep(2)
            
            # Scroll to make calendar visible
            self.driver.execute_script("window.scrollBy(0, 800)")
            time.sleep(1)

            # Use the exact XPath to find the date element
            date_xpath = "/html/body/div[1]/div/div/div/div[5]/div/div[2]/div/div/div/div[2]/button[32]"
            date_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, date_xpath))
            )
            
            # Get the date text for logging
            date_text = date_element.get_attribute('aria-label')
            logging.info(f"Found date element: {date_text}")
            
            # Scroll the date into view and click it
            self.driver.execute_script("arguments[0].scrollIntoView(true);", date_element)
            time.sleep(0.5)
            
            # Click the date
            date_element.click()
            logging.info(f"Clicked on date: {date_text}")
            time.sleep(1)
            
            # Use the exact XPath for the Book button
            book_button_xpath = "/html/body/div[1]/div/div/div/div[6]/div/div[1]/div/div[1]/button"
            book_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, book_button_xpath))
            )
            
            # Scroll the button into view and click it
            self.driver.execute_script("arguments[0].scrollIntoView(true);", book_button)
            time.sleep(0.5)
            
            # Try multiple click methods for the Book button
            try:
                book_button.click()
            except:
                self.driver.execute_script("arguments[0].click();", book_button)
            
            logging.info("Clicked Book button after date selection")
            
            # Wait for next screen
            time.sleep(2)
            
            # Now proceed to order type selection
            self.select_order_type()
            
        except Exception as e:
            logging.error(f"Error in date selection: {str(e)}")
            self.save_error_screenshot("date_selection_error.png")
            raise

    def select_time_slot(self):
        try:
            time.sleep(1)  # Wait for time slots to load
            
            # Get meal preference from env or default to dinner
            meal_pref = os.getenv('MEAL_PREFERENCE', 'DINNER').upper()
            desired_time = os.getenv('SLOT_PREFERENCE', '20:30')
            
            # Wait for time slots container
            time_slots_container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='time-slots-container']"))
            )
            
            # Find all available time slots
            time_slots = time_slots_container.find_elements(By.CSS_SELECTOR, "button[data-testid='time-slot']:not([disabled])")
            
            if not time_slots:
                raise ValueError("No available time slots found")
            
            # Try to find the desired time slot
            slot_found = False
            for slot in time_slots:
                slot_time = slot.get_attribute('data-time')
                if slot_time == desired_time:
                    slot.click()
                    slot_found = True
                    logging.info(f"Selected time slot: {desired_time}")
                    break
            
            # If desired slot not found, select the first available slot
            if not slot_found:
                time_slots[0].click()
                logging.info(f"Desired slot {desired_time} not found, selected first available slot")
            
            time.sleep(1)
            
            # Click continue after selecting time
            continue_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='continue-button']"))
            )
            continue_button.click()
            logging.info("Clicked continue after time selection")
            
        except Exception as e:
            logging.error(f"Error selecting time slot: {str(e)}")
            self.save_error_screenshot("time_slot_error.png")
            raise

    def select_order_type(self):
        try:
            # Wait for the slot selection page to load
            time.sleep(2)
            
            # Select time slot (2:30 PM)
            slot_xpath = "/html/body/div[1]/div/div/div/div[2]/div/div/div/span[2]"
            slot = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, slot_xpath))
            )
            slot.click()
            logging.info("Selected time slot: 2:30 PM")
            
            # Wait for continue button to be enabled and click it
            continue_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.Slots_continue_btn__3zieR"))
            )
            continue_button.click()
            logging.info("Clicked continue after slot selection")
            
            # Wait for form page to load
            time.sleep(2)
            
            # Fill in the form
            self.driver.find_element(By.XPATH, 
                "/html/body/div[1]/div/div/div/div[4]/div/div/form/div[4]/div/div/input").send_keys("Your Name")
            
            self.driver.find_element(By.XPATH, 
                "/html/body/div[1]/div/div/div/div[4]/div/div/form/div[5]/div/div/input").send_keys("your.email@example.com")
            
            self.driver.find_element(By.XPATH, 
                "/html/body/div[1]/div/div/div/div[4]/div/div/form/div[6]/div/div/input").send_keys("1234567890")
            
            self.driver.find_element(By.XPATH, 
                "/html/body/div[1]/div/div/div/div[4]/div/div/form/div[7]/div/div/textarea").send_keys("No special requests")
            
            # Accept terms
            terms_checkbox = self.driver.find_element(By.XPATH, 
                "/html/body/div[1]/div/div/div/div[4]/div/div/form/div[8]/div/div/input")
            self.driver.execute_script("arguments[0].click();", terms_checkbox)
            
            # Click final continue button
            final_continue = self.driver.find_element(By.XPATH, 
                "/html/body/div[1]/div/div/div/div[5]/button")
            final_continue.click()
            logging.info("Submitted booking form")
            
            # Wait for payment page
            time.sleep(2)
            
            # Select wallet payment
            wallet_option = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                    "/html/body/div/div[1]/div[2]/div[2]/div/div/div/div/div[1]/div[1]/label[6]/div"))
            )
            wallet_option.click()
            
            # Select Amazon Pay
            amazon_pay = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                    "/html/body/div/div[1]/div[2]/div[2]/div/div/div/div/div[2]/div/div/form/div/label[1]/div/div"))
            )
            amazon_pay.click()
            logging.info("Selected Amazon Pay payment method")
            
        except Exception as e:
            logging.error(f"Error in order type selection: {str(e)}")
            self.save_error_screenshot("order_type_error.png")
            raise

    def start_booking_process(self):
        try:
            logging.info("Starting booking process...")
            self.driver.get(os.getenv('BOOKING_URL'))
            
            # Select date
            self.select_date()
            
            # Select time slot
            self.select_time_slot()
            
            # Fill in guest details
            self.fill_guest_details()
            
            # Complete booking
            self.complete_booking()
            
        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            self.save_error_screenshot()
            raise
        finally:
            self.driver.quit()
            logging.info("Browser closed")

    def save_error_screenshot(self, filename="error.png"):
        """Save a screenshot when an error occurs"""
        try:
            self.driver.save_screenshot(filename)
            logging.info(f"Screenshot saved as {filename}")
        except Exception as e:
            logging.error(f"Failed to save screenshot: {str(e)}")

def run_booking():
    try:
        bot = EatNaruBookingBot()
        bot.start_booking_process()
    except Exception as e:
        logging.error(f"Booking attempt failed: {str(e)}")

def main():
    # Run immediately at script start
    run_booking()

if __name__ == "__main__":
    main() 