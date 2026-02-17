"""
Monitor ceny lotu – GitHub Actions
Ostatnia cena trzymana w last_price.txt w repo (git commit po każdej zmianie).
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

URL = (
    "https://biletyczarterowe.r.pl/destynacja"
    "?data=2026-02-22"
    "&dokad%5B%5D=PQC"
    "&idPrzylot=243424_382518"
    "&idWylot=382537"
    "&oneWay=false"
    "&pakietIdPrzylot=243424_382518"
    "&pakietIdWylot=243424_382537"
    "&przylotDo&przylotOd"
    "&wiek%5B%5D=1989-10-30"
    "&wylotDo&wylotOd"
    "#ZGF0YT0maWRXeWxvdD0zODI2NDcmb25lV2F5PWZhbHNlJnBha2lldElkV3lsb3Q9MjQzNDgyXzM4MjY0NyZwcnp5bG90RG8mcHJ6eWxvdE9kJndpZWslNUIlNUQ9MTk4OS0xMC0zMCZ3eWxvdERvJnd5bG90T2Q="
)

PRICE_FILE = "last_price.txt"
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


def scrape_price() -> str | None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ))
        try:
            log.info("Ładuję stronę...")
            page.goto(URL, timeout=60_000, wait_until="networkidle")
            page.wait_for_timeout(3000)

            body = page.inner_text("body")

            matches = re.findall(r"\d[\d\s]{1,7}(?:,\d{2})?\s*(?:zł|PLN)", body)
            for m in matches:
                digits = re.sub(r"\D", "", m)
                if len(digits) >= 3:
                    price = m.strip()
                    log.info(f"Znaleziono cenę: {price}")
                    return price

            log.warning("Nie znaleziono ceny.")
            log.debug(f"Fragment body: {body[:500]}")
            return None
        except Exception as e:
            log.error(f"Błąd scrapowania: {e}")
            return None
        finally:
            browser.close()


def load_last_price() -> str | None:
    if os.path.exists(PRICE_FILE):
        return open(PRICE_FILE, encoding="utf-8").read().strip() or None
    return None


def save_price(price: str):
    with open(PRICE_FILE, "w", encoding="utf-8") as f:
        f.write(price)


def main():
    now = datetime.now().strftime("%H:%M %d.%m.%Y")
    current_price = scrape_price()

    if current_price is None:
        log.warning("Nie udało się pobrać ceny.")
        send_telegram(f"⚠️ Nie udało się pobrać ceny lotu PQC o {now}.\nSprawdzę ponownie za 30 minut.")
        return

    last_price = load_last_price()
    log.info(f"Aktualna: {current_price} | Poprzednia: {last_price}")

    if last_price is None:
        save_price(current_price)
        send_telegram(
            f"✈️ <b>Monitor lotu PQC uruchomiony</b>\n"
            f"💰 Cena startowa: <b>{current_price}</b>\n"
            f"🕐 {now}"
        )
    elif current_price != last_price:
        save_price(current_price)
        send_telegram(
            f"🚨 <b>ZMIANA CENY LOTU do PQC!</b>\n"
            f"📌 Poprzednia: <s>{last_price}</s>\n"
            f"💰 Aktualna:  <b>{current_price}</b>\n"
            f"🕐 {now}\n"
            f'🔗 <a href="https://biletyczarterowe.r.pl">Sprawdź ofertę</a>'
        )
    else:
        log.info("Cena bez zmian – cicho.")


if __name__ == "__main__":
    main()
