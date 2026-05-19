"""
Naru Noodle Bar / Cafe Air - Booking Bot (CLI)
Playwright Firefox with stealth config | Razorpay payment automation

SETUP:
    pip install -r requirements.txt
    playwright install firefox
    python booking_bot.py
"""

import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt

from engine import BookingConfig, run_booking, SLOT_MAP, SEATING_MAP, VALID_SEATING

# ================================================================
# SETUP
# ================================================================

load_dotenv()
console = Console()
os.makedirs("logs", exist_ok=True)

log_file = f"logs/booking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=5),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("naru.cli")


# ================================================================
# INTERACTIVE CONFIG
# ================================================================

def collect_config() -> BookingConfig:
    """Collect booking details interactively with rich prompts."""
    console.print(Panel.fit(
        "[bold cyan]NARU NOODLE BAR[/bold cyan]\n[dim]Booking Bot Setup[/dim]",
        border_style="cyan",
    ))
    console.print()

    # Load defaults from .env or use fallbacks
    default_name = os.getenv("USER_NAME", "")
    default_email = os.getenv("USER_EMAIL", "")
    default_phone = os.getenv("USER_PHONE", "")
    default_slot = os.getenv("SLOT", "20:30")
    default_seating = os.getenv("SEATING", "TABLE2")
    default_guests = int(os.getenv("GUESTS", "2"))
    default_headless = os.getenv("HEADLESS", "false").lower() == "true"
    default_date = os.getenv("TARGET_DATE", (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

    # Collect user details
    name = Prompt.ask("  Your full name", default=default_name or None)
    while not name:
        console.print("  [red]Name is required[/red]")
        name = Prompt.ask("  Your full name")

    email = Prompt.ask("  Email", default=default_email or None)
    while not email or "@" not in email:
        console.print("  [red]Valid email required[/red]")
        email = Prompt.ask("  Email")

    phone = Prompt.ask("  Phone (10 digits, no +91)", default=default_phone or None)
    while not phone or not phone.isdigit() or len(phone) != 10:
        console.print("  [red]Must be exactly 10 digits[/red]")
        phone = Prompt.ask("  Phone (10 digits)")

    # Booking preferences
    console.print(f"\n  [dim]Available slots:[/dim] {' | '.join(SLOT_MAP.keys())}")
    slot = Prompt.ask("  Time slot", default=default_slot, choices=list(SLOT_MAP.keys()))

    console.print(f"  [dim]Seating options:[/dim]")
    for key, label in SEATING_MAP.items():
        console.print(f"    {key} = {label}")
    seating = Prompt.ask("  Seating", default=default_seating, choices=VALID_SEATING)

    guests = IntPrompt.ask("  Guests (1-5)", default=default_guests)
    while guests < 1 or guests > 5:
        console.print("  [red]Must be 1-5[/red]")
        guests = IntPrompt.ask("  Guests (1-5)")

    target_date = Prompt.ask("  Date (YYYY-MM-DD)", default=default_date)
    special_requests = Prompt.ask("  Special requests", default="")

    headless_str = Prompt.ask("  Run headless?", default="n" if not default_headless else "y", choices=["y", "n"])
    headless = headless_str == "y"

    cfg = BookingConfig(
        name=name,
        email=email,
        phone=phone,
        slot=slot,
        seating=seating,
        guests=guests,
        target_date=target_date,
        special_requests=special_requests,
        headless=headless,
    )

    console.print()
    console.print(Panel(
        f"[bold]{slot}[/bold] | {seating} | {guests} guests | {target_date}\n"
        f"[dim]{name} | {email} | {phone}[/dim]",
        title="Booking Summary",
        border_style="green",
    ))
    console.print()

    confirm = Prompt.ask("  Start booking?", default="y", choices=["y", "n"])
    if confirm != "y":
        console.print("  [yellow]Cancelled.[/yellow]")
        sys.exit(0)

    return cfg


# ================================================================
# MAIN
# ================================================================

async def main():
    cfg = collect_config()
    console.print(f"\n  [dim]Log file: {log_file}[/dim]\n")

    result = await run_booking(cfg)

    if result.status == "success":
        console.print(Panel(f"[bold green]{result.message}[/bold green]", border_style="green"))
    elif result.status == "partial":
        console.print(Panel(
            f"[bold yellow]{result.message}[/bold yellow]\n"
            f"[dim]Payment URL: {result.payment_url}[/dim]",
            border_style="yellow",
        ))
    else:
        console.print(Panel(f"[bold red]{result.message}[/bold red]", border_style="red"))
        if result.screenshot:
            console.print(f"  [dim]Screenshot: {result.screenshot}[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
