# Invest Academy

Learn to invest, then practice with $1,000 in fake money. Flask + SQLite, no Node.js required.

## Run it

```bash
cd ~/invest-academy
source venv/bin/activate
python run.py
```

Then open http://127.0.0.1:5050

## Add live stock prices (optional)

Without an API key, the market uses realistic simulated prices, so the app works out of the box.
For real, live quotes:

1. Go to https://finnhub.io/register and create a free account (no credit card required).
2. Copy your API key from the Finnhub dashboard.
3. Open `.env` in this folder and set:
   ```
   FINNHUB_API_KEY=your_key_here
   ```
4. Restart the app.

## Project layout

- `app/auth` — signup/login (Flask-Login, SQLite)
- `app/learning` — videos, articles, investor tips content
- `app/practice` — trading, portfolio, leveling/badges
- `app/templates`, `app/static` — HTML/CSS/JS
- `instance/invest_academy.db` — SQLite database (created automatically)
