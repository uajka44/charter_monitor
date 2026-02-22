# Flight Monitor – Monitor Cen Lotów ✈️

Automatyczny monitor cen lotów czarterowych. Sprawdza co 30 minut, wysyła alerty przez Telegram.

## Jak to działa

1. Edytujesz plik **`flights.json`** — dodajesz URL lotu i ustawiasz `active: true`
2. Skrypt sam wyciąga ze strony:
   - Nazwę miejsca (Cancun, Phu Quoc, etc.)
   - Datę wylotu i powrotu
   - Cenę z buttona "Wybieram za X zł"
3. Zapisuje ostatnią cenę w folderze `prices/`
4. Gdy cena się zmieni → alert na Telegram 🚨

## Setup (jednorazowo)

### 1. GitHub Secrets
**Settings → Secrets and variables → Actions → New repository secret**

| Nazwa | Wartość |
|-------|---------|
| `TELEGRAM_BOT_TOKEN` | token od BotFather |
| `TELEGRAM_CHAT_ID` | twoje chat_id |

### 2. Edytuj `flights.json`
Dodaj swoje loty:

```json
[
  {
    "active": true,
    "url": "https://biletycharterowe.r.pl/destynacja?data=2026-02-26&dokad%5B%5D=CUN&..."
  },
  {
    "active": false,
    "url": "https://..."
  }
]
```

### 3. Commit i Push
```bash
git add .
git commit -m "update flights"
git push
```

## Zarządzanie lotami

### Dodanie nowego lotu
1. Skopiuj URL ze strony biletyczarterowe.r.pl
2. Edytuj `flights.json` (możesz na GitHubie lub lokalnie)
3. Dodaj blok:
```json
{
  "active": true,
  "url": "WKLEJ_URL_TUTAJ"
}
```
4. Zapisz, commit, push

### Wyłączenie lotu
Zmień `"active": true` na `"active": false`

### Usunięcie lotu
Usuń cały blok `{}` z pliku JSON

## Struktura
```
flight-monitor/
├── .github/workflows/monitor.yml   ← harmonogram
├── flights.json                    ← twoje loty (edytujesz TEN plik)
├── flight_monitor.py               ← skrypt
├── prices/                         ← ostatnie ceny (auto)
└── README.md
```

## Test
**Actions → Monitor Ceny Lotu → Run workflow**

Dostaniesz wiadomość dla każdego aktywnego lotu.
