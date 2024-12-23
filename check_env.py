import os
from dotenv import load_dotenv
import logging

def check_environment():
    load_dotenv()
    
    required_vars = {
        'USER_NAME': 'Your full name',
        'USER_EMAIL': 'Your email address',
        'USER_PHONE': 'Your 10-digit phone number',
        'BOOKING_URL': 'The booking website URL',
        'GUESTS': 'Number of guests',
        'SLOT_PREFERENCE': 'Your preferred time slot (12:30, 14:30, 18:30, 20:30)',
        'SPECIAL_REQUESTS': 'Any special requests for the booking',
        'PAYMENT_METHOD': 'Payment method (currently only AMAZON_PAY)'
    }
    
    missing_vars = []
    invalid_vars = []
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            missing_vars.append(f"{var} ({description})")
        elif var == 'USER_PHONE' and (not value.isdigit() or len(value) != 10):
            invalid_vars.append(f"{var}: Invalid phone number format")
        elif var == 'USER_EMAIL' and '@' not in value:
            invalid_vars.append(f"{var}: Invalid email format")
        elif var == 'SLOT_PREFERENCE' and value not in ['12:30', '14:30', '18:30', '20:30']:
            invalid_vars.append(f"{var}: Must be one of: 12:30, 14:30, 18:30, 20:30")
        elif var == 'PAYMENT_METHOD' and value != 'AMAZON_PAY':
            invalid_vars.append(f"{var}: Currently only AMAZON_PAY is supported")
        elif var == 'GUESTS':
            try:
                guests = int(value)
                if guests < 1:
                    invalid_vars.append(f"{var}: Must be at least 1")
            except ValueError:
                invalid_vars.append(f"{var}: Must be a valid number")
    
    if missing_vars or invalid_vars:
        print("\n❌ Environment Check Failed!")
        if missing_vars:
            print("\nMissing Variables:")
            for var in missing_vars:
                print(f"- {var}")
        if invalid_vars:
            print("\nInvalid Variables:")
            for var in invalid_vars:
                print(f"- {var}")
        return False
    
    print("\n✅ Environment Check Passed!")
    print("\nCurrent Configuration:")
    for var in required_vars:
        value = os.getenv(var)
        # Mask sensitive information
        if var in ['USER_PHONE', 'USER_EMAIL']:
            value = f"{value[:3]}...{value[-3:]}"
        print(f"- {var}: {value}")
    return True

if __name__ == "__main__":
    check_environment() 