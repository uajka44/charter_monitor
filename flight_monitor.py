"""
Monitor cen lotów – GitHub Actions
Monitoruje wiele lotów jednocześnie, każdy zapisany w osobnym pliku.
"""

import os
import re
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright
import requests

# ── Konfiguracja (GitHub Secrets) ───────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]

# Lista lotów do monitorowania
FLIGHTS = [
    {
        "name": "PQC (Phu Quoc)",
        "url": (
            "https://biletyczarterowe.r.pl/destynacja"
            "?data=2026-02-20"
            "&dokad%5B%5D=PQC"
            "&idPrzylot=243559_382561"
            "&idWylot=382585"
            "&oneWay=false"
            "&pakietIdPrzylot=243559_382561"
            "&pakietIdWylot=243559_382585"
            "&przylotDo&przylotOd"
            "&wiek%5B%5D=1989-10-30"
            "&wylotDo&wylotOd"
            "#ZGF0YT0maWRXeWxvdD0zODI2NDcmb25lV2F5PWZhbHNlJnBha2lldElkV3lsb3Q9MjQzNDgyXzM4MjY0NyZwcnp5bG90RG8mcHJ6eWxvdE9kJndpZWslNUIlNUQ9MTk4OS0xMC0zMCZ3eWxvdERvJnd5bG90T2Q="
        ),
        "price_file": "last_price_pqc.txt"
    },
    {
        "name": "CUN (Cancun)",
        "url": (
            "https://biletyczarterowe.r.pl/destynacja"
            "?data=2026-03-01"
            "&dokad%5B%5D=CUN"
            "&idPrzylot=247774_382419"
            "&idWylot=382444"
            "&oneWay=false"
            "&pakietIdPrzylot=247774_382419"
            "&pakietIdWylot=247774_382444"
            "&przylotDo&przylotOd"
            "&wiek%5B%5D=1989-10-30"
            "&wylotDo&wylotOd"
        ),
        "price_file": "last_price_cun.txt"
    }
]
# ────────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }, timeout=15)
    r.raise_for_status()
    log.info("Telegram: wysłano.")


def scrape_price(url: str) -> str | None:
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

            # Główny selektor
            el = page.query_selector("strong[data-v-38925441]")
            if el:
                price = el.inner_text().strip()
                log.info(f"Znaleziono cenę: {price}")
                return price

            # Fallback
            log.warning("Główny selektor nie znalazł ceny, próbuję fallback...")
            elements = page.query_selector_all("strong")
            for el in elements:
                text = el.inner_text().strip()
                if re.search(r"\d[\d\s]*zł", text) and len(text) < 20:
                    log.info(f"Fallback - znaleziono: {text}")
                    return text

            log.warning("Nie znaleziono ceny.")
            return None

        except Exception as e:
            log.error(f"Błąd scrapowania: {e}")
            return None
        finally:
            browser.close()


def load_last_price(filepath: str) -> str | None:
    if os.path.exists(filepath):
        return open(filepath, encoding="utf-8").read().strip() or None
    return None


def save_price(filepath: str, price: str):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(price)


def check_flight(flight: dict):
    """Sprawdź jeden lot i wyślij powiadomienie jeśli cena się zmieniła."""
    name = flight["name"]
    url = flight["url"]
    price_file = flight["price_file"]
    
    log.info(f"=== Sprawdzam lot: {name} ===")
    now = datetime.now().strftime("%H:%M %d.%m.%Y")
    
    current_price = scrape_price(url)

    if current_price is None:
        log.warning(f"{name}: Nie udało się pobrać ceny.")
        send_telegram(f"⚠️ Nie udało się pobrać ceny lotu <b>{name}</b> o {now}.")
        return

    last_price = load_last_price(price_file)
    log.info(f"{name}: Aktualna: {current_price} | Poprzednia: {last_price}")

    if last_price is None:
        save_price(price_file, current_price)
        send_telegram(
            f"✈️ <b>Monitor lotu {name}</b>\n"
            f"💰 Cena startowa: <b>{current_price}</b>\n"
            f"🕐 {now}"
        )
    elif current_price != last_price:
        save_price(price_file, current_price)
        send_telegram(
            f"🚨 <b>ZMIANA CENY!</b>\n"
            f"✈️ Lot: <b>{name}</b>\n"
            f"📌 Poprzednia: <s>{last_price}</s>\n"
            f"💰 Aktualna:  <b>{current_price}</b>\n"
            f"🕐 {now}\n"
            f'🔗 <a href="{url[:80]}">Sprawdź ofertę</a>'
        )
    else:
        log.info(f"{name}: Cena bez zmian – cicho.")


def main():
    log.info("=== Start monitora lotów ===")
    for flight in FLIGHTS:
        check_flight(flight)
        log.info("")  # pusta linia między lotami


if __name__ == "__main__":
    main()
