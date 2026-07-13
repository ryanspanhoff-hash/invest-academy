import hashlib
import math
import time

import requests
from flask import current_app

STOCKS = [
    {"symbol": "AAPL", "name": "Apple Inc.", "base_price": 210.0},
    {"symbol": "MSFT", "name": "Microsoft Corp.", "base_price": 425.0},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "base_price": 175.0},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "base_price": 185.0},
    {"symbol": "TSLA", "name": "Tesla Inc.", "base_price": 245.0},
    {"symbol": "NVDA", "name": "NVIDIA Corp.", "base_price": 135.0},
    {"symbol": "META", "name": "Meta Platforms Inc.", "base_price": 495.0},
    {"symbol": "NFLX", "name": "Netflix Inc.", "base_price": 660.0},
    {"symbol": "DIS", "name": "Walt Disney Co.", "base_price": 110.0},
    {"symbol": "KO", "name": "Coca-Cola Co.", "base_price": 63.0},
    {"symbol": "PEP", "name": "PepsiCo Inc.", "base_price": 170.0},
    {"symbol": "WMT", "name": "Walmart Inc.", "base_price": 68.0},
    {"symbol": "NKE", "name": "Nike Inc.", "base_price": 78.0},
    {"symbol": "MCD", "name": "McDonald's Corp.", "base_price": 290.0},
    {"symbol": "SBUX", "name": "Starbucks Corp.", "base_price": 95.0},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "base_price": 205.0},
    {"symbol": "V", "name": "Visa Inc.", "base_price": 275.0},
    {"symbol": "MA", "name": "Mastercard Inc.", "base_price": 460.0},
    {"symbol": "BA", "name": "Boeing Co.", "base_price": 180.0},
    {"symbol": "XOM", "name": "Exxon Mobil Corp.", "base_price": 115.0},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "base_price": 150.0},
    {"symbol": "PFE", "name": "Pfizer Inc.", "base_price": 28.0},
    {"symbol": "INTC", "name": "Intel Corp.", "base_price": 32.0},
    {"symbol": "AMD", "name": "Advanced Micro Devices", "base_price": 145.0},
]

STOCK_LOOKUP = {s["symbol"]: s for s in STOCKS}

_cache = {}
CACHE_TTL_SECONDS = 20


def _simulated_price(symbol: str, base_price: float) -> float:
    """Deterministic-ish random walk so prices move smoothly without an API key."""
    seed = int(hashlib.sha256(symbol.encode()).hexdigest(), 16) % 100000
    t = time.time() / 45.0
    wave = math.sin(t + seed) * 0.015 + math.sin(t * 0.37 + seed * 0.5) * 0.01
    price = base_price * (1 + wave)
    return round(max(price, 0.5), 2)


def _fetch_finnhub_price(symbol: str):
    api_key = current_app.config.get("FINNHUB_API_KEY")
    if not api_key:
        return None
    try:
        resp = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": symbol, "token": api_key},
            timeout=4,
        )
        resp.raise_for_status()
        data = resp.json()
        price = data.get("c")
        if price and price > 0:
            return {
                "price": round(price, 2),
                "change": round(data.get("d", 0.0) or 0.0, 2),
                "percent_change": round(data.get("dp", 0.0) or 0.0, 2),
                "live": True,
            }
    except (requests.RequestException, ValueError):
        pass
    return None


def get_quote(symbol: str) -> dict:
    symbol = symbol.upper()
    stock = STOCK_LOOKUP.get(symbol)
    if not stock:
        return None

    cached = _cache.get(symbol)
    if cached and (time.time() - cached["ts"]) < CACHE_TTL_SECONDS:
        return cached["quote"]

    live = _fetch_finnhub_price(symbol)
    if live:
        quote = {
            "symbol": symbol,
            "name": stock["name"],
            "price": live["price"],
            "change": live["change"],
            "percent_change": live["percent_change"],
            "live": True,
        }
    else:
        price = _simulated_price(symbol, stock["base_price"])
        prev = _cache.get(symbol, {}).get("quote", {}).get("price", stock["base_price"])
        quote = {
            "symbol": symbol,
            "name": stock["name"],
            "price": price,
            "change": round(price - prev, 2),
            "percent_change": round(((price - prev) / prev) * 100, 2) if prev else 0.0,
            "live": False,
        }

    _cache[symbol] = {"ts": time.time(), "quote": quote}
    return quote


def get_all_quotes() -> list:
    return [get_quote(s["symbol"]) for s in STOCKS]


def portfolio_net_worth(portfolio) -> float:
    total = portfolio.cash
    for holding in portfolio.holdings:
        quote = get_quote(holding.symbol)
        price = quote["price"] if quote else holding.avg_cost
        total += holding.quantity * price
    return round(total, 2)
