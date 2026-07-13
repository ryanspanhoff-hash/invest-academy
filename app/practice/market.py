import hashlib
import math
import time
from concurrent.futures import ThreadPoolExecutor

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
    """Fetches all quotes concurrently. Sequentially, 24 symbols each with a
    multi-second network timeout could take well over a minute in the worst
    case (all cache misses, slow upstream) — long enough to trip a request
    timeout and 502 every visitor at once. Threads keep the worst case near
    a single request's timeout instead of the sum of all of them."""
    app = current_app._get_current_object()

    def _fetch(symbol):
        with app.app_context():
            return get_quote(symbol)

    with ThreadPoolExecutor(max_workers=8) as executor:
        quotes = list(executor.map(_fetch, [s["symbol"] for s in STOCKS]))
    return quotes


def portfolio_net_worth(portfolio) -> float:
    total = portfolio.cash
    for holding in portfolio.holdings:
        quote = get_quote(holding.symbol)
        price = quote["price"] if quote else holding.avg_cost
        total += holding.quantity * price
    return round(total, 2)


HISTORY_RANGES = {
    "1d": {"range": "1d", "interval": "5m", "label": "1D"},
    "1w": {"range": "5d", "interval": "30m", "label": "1W"},
    "1m": {"range": "1mo", "interval": "1d", "label": "1M"},
    "1y": {"range": "1y", "interval": "1wk", "label": "1Y"},
}

_history_cache = {}
HISTORY_CACHE_TTL_SECONDS = 300


def _fetch_real_history(symbol: str, range_key: str):
    spec = HISTORY_RANGES[range_key]
    try:
        resp = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"range": spec["range"], "interval": spec["interval"]},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5,
        )
        resp.raise_for_status()
        result = resp.json()["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        points = [
            {"t": t, "price": round(c, 2)}
            for t, c in zip(timestamps, closes)
            if c is not None
        ]
        if points:
            return points
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
        pass
    return None


def _simulated_history(symbol: str, base_price: float, range_key: str):
    """Deterministic simulated price series, ending at the current simulated price,
    used whenever real historical data can't be fetched."""
    spec = HISTORY_RANGES[range_key]
    num_points = 60
    span_seconds = {"1d": 86400, "1w": 7 * 86400, "1m": 30 * 86400, "1y": 365 * 86400}[range_key]
    seed = int(hashlib.sha256(symbol.encode()).hexdigest(), 16) % 100000
    now = time.time()
    points = []
    for i in range(num_points + 1):
        t = now - span_seconds * (1 - i / num_points)
        wave = math.sin(t / 45.0 + seed) * 0.015 + math.sin(t / 45.0 * 0.37 + seed * 0.5) * 0.01
        drift = math.sin(t / span_seconds * math.pi + seed * 0.2) * 0.06
        price = base_price * (1 + wave + drift)
        points.append({"t": int(t), "price": round(max(price, 0.5), 2)})
    return points


def get_history(symbol: str, range_key: str) -> dict:
    symbol = symbol.upper()
    stock = STOCK_LOOKUP.get(symbol)
    if not stock or range_key not in HISTORY_RANGES:
        return None

    cache_key = f"{symbol}:{range_key}"
    cached = _history_cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < HISTORY_CACHE_TTL_SECONDS:
        return cached["data"]

    points = _fetch_real_history(symbol, range_key)
    live = points is not None
    if not points:
        points = _simulated_history(symbol, stock["base_price"], range_key)

    data = {"symbol": symbol, "range": range_key, "live": live, "points": points}
    _history_cache[cache_key] = {"ts": time.time(), "data": data}
    return data
