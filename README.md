# Flight Monitor – Monitor Ceny Lotu ✈️

Sprawdza cenę lotu do PQC co 30 minut. Powiadomienia przez Telegram.
Ostatnia cena zapisywana w `last_price.txt` w repo – zero zewnętrznych serwisów.

## Setup (jednorazowo)

### 1. Utwórz repo na GitHub
Nowe repo: `flight-monitor` (może być prywatne)

### 2. Dodaj GitHub Secrets
**Settings → Secrets and variables → Actions → New repository secret**

| Nazwa | Wartość |
|-------|---------|
| `TELEGRAM_BOT_TOKEN` | token od BotFather |
| `TELEGRAM_CHAT_ID` | `422204159` |

### 3. Wgraj pliki na GitHub
```bash
cd C:\Users\anasy\Github\flight-monitor
git init
git add .
git commit -m "init"
git remote add origin https://github.com/TWOJ_LOGIN/flight-monitor.git
git push -u origin main
```

### 4. Pierwsze uruchomienie
Ręcznie: **Actions → Monitor Ceny Lotu → Run workflow**

## Jak to działa
- Co 30 minut GitHub odpala skrypt
- Skrypt ładuje stronę przez Playwright (headless Chrome)
- Porównuje cenę z `last_price.txt`
- Jeśli zmiana → wysyła alert Telegram 🚨
- Zapisuje nową cenę do `last_price.txt` (git commit do repo)

## Struktura
```
flight-monitor/
├── .github/workflows/monitor.yml   ← harmonogram
├── flight_monitor.py               ← skrypt
├── last_price.txt                  ← aktualna cena (auto-aktualizowana)
└── README.md
```
