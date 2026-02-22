"""
Monitor cen lotów – GitHub Actions
Pobiera dane z flights.json, automatycznie wyciąga szczegóły lotu.
"""

import os
import re
import json
import hashlib
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright
import requests

# ── Konfiguracja ────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
FLIGHTS_FILE       = "flights.json"
PRICE_DIR          = "prices"
# ────────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)


def send_telegram(message: str):
    """Wyślij wiadomość przez Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }, timeout=15)
    r.raise_for_status()
    log.info("Telegram: wysłano.")


def extract_date_from_url(url: str) -> str:
    """Wyciągnij datę wylotu z parametru URL data=YYYY-MM-DD."""
    match = re.search(r'data=(\d{4}-\d{2}-\d{2})', url)
    return match.group(1) if match else "Brak daty"


def parse_flight_page(url: str) -> dict | None:
    """
    Otwórz stronę i wyciągnij:
    - destination (z h1.breadcrumbs__header-title)
    - price (z buttona "Wybieram za X zł")
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ))
        try:
            log.info(f"Ładuję stronę: {url[:60]}...")
            page.goto(url, timeout=60_000, wait_until="networkidle")
            page.wait_for_timeout(4000)

            # Destination
            destination_el = page.query_selector("h1.breadcrumbs__header-title")
            destination = destination_el.inner_text().strip() if destination_el else "Nieznane"

            # Cena z buttona "Wybieram za X zł"
            price = None
            buttons = page.query_selector_all("a.button, a.kupuje-button")
            for btn in buttons:
                text = btn.inner_text().strip()
                # Szukamy "Wybieram za 3500 zł"
                match = re.search(r'Wybieram za ([\d\s]+zł)', text)
                if match:
                    price = match.group(1).strip()
                    break

            if not price:
                log.warning("Nie znaleziono ceny w buttonie, próbuję fallback...")
                # Fallback - szukamy w strong
                el = page.query_selector("strong[data-v-38925441]")
                if el:
                    price = el.inner_text().strip()

            if not price:
                log.warning("Nie znaleziono ceny na stronie.")
                return None

            log.info(f"Wyciągnięto: {destination}, {price}")
            return {
                "destination": destination,
                "price": price
            }

        except Exception as e:
            log.error(f"Błąd parsowania: {e}")
            return None
        finally:
            browser.close()


def get_flight_id(url: str) -> str:
    """Generuj unikalny ID lotu z URL (hash)."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def load_last_price(flight_id: str) -> str | None:
    """Wczytaj ostatnią cenę dla danego lotu."""
    filepath = os.path.join(PRICE_DIR, f"{flight_id}.txt")
    if os.path.exists(filepath):
        return open(filepath, encoding="utf-8").read().strip() or None
    return None


def save_price(flight_id: str, price: str):
    """Zapisz cenę dla danego lotu."""
    os.makedirs(PRICE_DIR, exist_ok=True)
    filepath = os.path.join(PRICE_DIR, f"{flight_id}.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(price)


def check_flight(url: str):
    """Sprawdź jeden lot i wyślij powiadomienie jeśli cena się zmieniła."""
    flight_id = get_flight_id(url)
    log.info(f"=== Sprawdzam lot (ID: {flight_id}) ===")
    
    # Data wylotu z URL
    departure_date = extract_date_from_url(url)
    
    data = parse_flight_page(url)
    if not data:
        send_telegram(f"⚠️ Nie udało się pobrać danych dla lotu:\n{url[:80]}")
        return

    destination = data["destination"]
    current_price = data["price"]
    now = datetime.now().strftime("%H:%M %d.%m.%Y")

    last_price = load_last_price(flight_id)
    log.info(f"{destination}: Aktualna: {current_price} | Poprzednia: {last_price}")

    if last_price is None:
        # Pierwsze sprawdzenie
        save_price(flight_id, current_price)
        send_telegram(
            f"✈️ <b>Nowy lot w monitoringu</b>\n"
            f"📍 {destination}\n"
            f"📅 Wylot: {departure_date}\n"
            f"💰 Cena: <b>{current_price}</b>\n"
            f"🕐 {now}"
        )
    elif current_price != last_price:
        # Zmiana ceny!
        save_price(flight_id, current_price)
        send_telegram(
            f"🚨 <b>ZMIANA CENY!</b>\n"
            f"✈️ {destination}\n"
            f"📅 Wylot: {departure_date}\n"
            f"📌 Poprzednia: <s>{last_price}</s>\n"
            f"💰 Aktualna:  <b>{current_price}</b>\n"
            f"🕐 {now}\n"
            f'🔗 <a href="{url[:100]}">Sprawdź ofertę</a>'
        )
    else:
        log.info(f"{destination}: Cena bez zmian – cicho.")


def main():
    log.info("=== Start monitora lotów ===")
    
    # Wczytaj flights.json
    if not os.path.exists(FLIGHTS_FILE):
        log.error(f"Brak pliku {FLIGHTS_FILE}!")
        send_telegram(f"⚠️ Błąd: brak pliku {FLIGHTS_FILE}")
        return

    with open(FLIGHTS_FILE, encoding="utf-8") as f:
        flights = json.load(f)

    active_flights = [f for f in flights if f.get("active", False)]
    log.info(f"Znaleziono {len(active_flights)} aktywnych lotów.")

    for flight in active_flights:
        url = flight.get("url")
        if not url:
            log.warning("Lot bez URL - pomijam.")
            continue
        check_flight(url)
        log.info("")


if __name__ == "__main__":
    main()
