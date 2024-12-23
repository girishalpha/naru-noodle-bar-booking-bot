

# Eat Naru Booking Bot

An automated booking system for **Eat Naru** and other AirMenu-powered restaurant booking sites using Selenium WebDriver.

## Welcome Contributors 🎉
### WIP
Contributions are welcome to expand support for more booking platforms and features.


This bot is currently designed for **Eat Naru**, but testing is only possible on Mondays. In the meantime, work is ongoing to adapt and test it for another AirMenu-powered site.

- **Target Site**: Cafe Air Booking  
- **Update `.env`**:  
  ```env
  BOOKING_URL=https://bookings.airmenus.in/CafeAir/CafeAir
  ```

Steps to adapt and test for the new site:

1. Update the `BOOKING_URL` in the `.env` file with the URL of the new site.
2. Modify XPath or CSS selectors in `booking_bot.py` to align with the new site's specific elements.
3. Run the bot on the new site and document any discrepancies encountered during testing.


## Prerequisites

- **Python Version**: 3.x
- **Browser**: Chrome (Ensure it's up to date)
- **Python Packages** (install via `pip install -r requirements.txt`):
  - `selenium-wire`
  - `selenium`
  - `webdriver-manager`
  - `python-dotenv`
  - `schedule`



## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a `.env` File**

   Add the following variables in the `.env` file:

   ```env
   # General Booking Details
   BOOKING_URL=<restaurant booking URL>
   USER_NAME=<your name>
   USER_EMAIL=<your email>
   USER_PHONE=<10-digit phone number>
   GUESTS=<number of guests>
   MEAL_PREFERENCE=<LUNCH or DINNER>
   SLOT_PREFERENCE=<12:30, 14:30, 18:30, or 20:30>
   SEATING_PREFERENCE=RAMEN

   # Payment
   PAYMENT_METHOD=AmazonPay # Future options: CreditCard, Wallet, etc.
   ```

4. **Run the Bot**
   ```bash
   python booking_bot.py
   ```


## Booking Process

The bot automates the following steps:

1. Navigates to the booking URL at the scheduled time.
2. Scrolls to the booking calendar.
3. Selects the desired date.
4. Chooses seating preference:
   - **RAMEN BAR SEATING** (₹1000, redeemable; Max: 3 guests)
   - **TABLE OPTIONS** (₹5000, redeemable; Max: 4 guests)
5. Selects the time slot and guest count.
6. Fills in user details:
   - Name
   - Email
   - Phone number
   - Special requests (optional)
7. Accepts terms and conditions.
8. Handles payment via the specified method (default: Amazon Pay Wallet).
9. Confirms and logs booking details.


## Notes

- **Seating Limits**:
  - RAMEN BAR: Max 3 guests
  - Tables: Max 4 guests
- **Booking Amount**: Fully redeemable against the food bill.
- **Supported Payment Methods**: Currently supports Amazon Pay Wallet. Future updates will include additional payment options.


## Contributing

1. Fork the repository.
2. Create a new feature branch.
3. Commit your changes.
4. Submit a pull request with a detailed description of your updates.

