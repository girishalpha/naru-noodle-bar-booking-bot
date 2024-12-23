# Eat Naru Booking Bot

An automated booking system for Eat Naru restaurant using Selenium WebDriver.

## Prerequisites

- Python 3.x
- Chrome browser
- Required Python packages (install via `pip install -r requirements.txt`):
  - selenium-wire
  - selenium
  - webdriver-manager
  - python-dotenv
  - schedule

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file with the following variables:


BOOKING_URL=<restaurant booking URL>
USER_NAME=<your name>
USER_EMAIL=<your email>
USER_PHONE=<10-digit phone number>
GUESTS=<number of guests>
MEAL_PREFERENCE=<LUNCH or DINNER>
SLOT_PREFERENCE=<12:30, 14:30, 18:30, or 20:30>
SEATING_PREFERENCE=RAMEN

```

## Booking Process

The bot automates the following steps:

1. Opens the booking URL at the specified time
2. Scrolls down to access the booking calendar
3. Selects the desired date
4. Chooses seating preference:
   - RAMEN BAR SEATING (₹1000, redeemable)
   - TABLE options (₹5000, redeemable)
5. Selects time slot and number of guests
6. Fills in personal details:
   - Name
   - Email
   - Phone number
   - Special requests
   - Accepts terms and conditions
7. Handles payment via Amazon Pay wallet

## Error Handling

- The bot saves screenshots on errors for debugging
- Logs are written to `booking_bot.log`
- Comprehensive error messages are displayed in the console

## Notes

- Maximum 3 guests for RAMEN BAR SEATING
- Tables seat up to 4 guests
- Booking amounts are fully redeemable against the food bill

## Usage

Run the bot:
