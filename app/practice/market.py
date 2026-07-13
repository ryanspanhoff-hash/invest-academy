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

CRYPTO = [
    {"symbol": "BTC-USD", "name": "Bitcoin", "base_price": 64000.0},
    {"symbol": "ETH-USD", "name": "Ethereum", "base_price": 1800.0},
    {"symbol": "SOL-USD", "name": "Solana", "base_price": 78.0},
    {"symbol": "DOGE-USD", "name": "Dogecoin", "base_price": 0.075},
    {"symbol": "XRP-USD", "name": "XRP", "base_price": 1.1},
    {"symbol": "ADA-USD", "name": "Cardano", "base_price": 0.16},
    {"symbol": "AVAX-USD", "name": "Avalanche", "base_price": 6.5},
    {"symbol": "LTC-USD", "name": "Litecoin", "base_price": 44.0},
    {"symbol": "LINK-USD", "name": "Chainlink", "base_price": 8.1},
    {"symbol": "DOT-USD", "name": "Polkadot", "base_price": 0.85},
]

STOCK_LOOKUP = {s["symbol"]: s for s in STOCKS}
CRYPTO_LOOKUP = {c["symbol"]: c for c in CRYPTO}

_cache = {}
CACHE_TTL_SECONDS = 20

# Symbols outside the curated lists have no hardcoded base_price for simulated
# fallback — this remembers the first real price we ever saw for one, so
# simulation can still work smoothly if a later live fetch fails.
_dynamic_base_price = {}
_dynamic_name = {}


def is_crypto(symbol: str) -> bool:
    return symbol.upper().endswith("-USD")


def _known_name(symbol: str):
    symbol = symbol.upper()
    if symbol in STOCK_LOOKUP:
        return STOCK_LOOKUP[symbol]["name"]
    if symbol in CRYPTO_LOOKUP:
        return CRYPTO_LOOKUP[symbol]["name"]
    return _dynamic_name.get(symbol)


def get_name(symbol: str) -> str:
    return _known_name(symbol) or symbol.upper()


def _known_base_price(symbol: str):
    symbol = symbol.upper()
    if symbol in STOCK_LOOKUP:
        return STOCK_LOOKUP[symbol]["base_price"]
    if symbol in CRYPTO_LOOKUP:
        return CRYPTO_LOOKUP[symbol]["base_price"]
    return _dynamic_base_price.get(symbol)


def _simulated_price(symbol: str, base_price: float) -> float:
    """Deterministic-ish random walk so prices move smoothly without an API key."""
    seed = int(hashlib.sha256(symbol.encode()).hexdigest(), 16) % 100000
    t = time.time() / 45.0
    wave = math.sin(t + seed) * 0.015 + math.sin(t * 0.37 + seed * 0.5) * 0.01
    price = base_price * (1 + wave)
    return round(max(price, 0.000001), 6 if price < 1 else 2)


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


def _fetch_yahoo_price(symbol: str, name_hint: str = None):
    try:
        resp = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"range": "1d", "interval": "5m"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5,
        )
        resp.raise_for_status()
        meta = resp.json()["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice")
        prev = meta.get("previousClose") or meta.get("chartPreviousClose")
        if price:
            if meta.get("shortName"):
                _dynamic_name.setdefault(symbol.upper(), meta["shortName"])
            change = round(price - prev, 2) if prev else 0.0
            pct = round((change / prev) * 100, 2) if prev else 0.0
            return {"price": round(price, 6 if price < 1 else 2), "change": change, "percent_change": pct, "live": True}
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
        pass
    return None


def get_quote(symbol: str) -> dict:
    symbol = symbol.upper()

    cached = _cache.get(symbol)
    if cached and (time.time() - cached["ts"]) < CACHE_TTL_SECONDS:
        return cached["quote"]

    live = _fetch_yahoo_price(symbol) if is_crypto(symbol) else (_fetch_finnhub_price(symbol) or _fetch_yahoo_price(symbol))

    if live:
        _dynamic_base_price.setdefault(symbol, live["price"])
        quote = {
            "symbol": symbol,
            "name": get_name(symbol),
            "price": live["price"],
            "change": live["change"],
            "percent_change": live["percent_change"],
            "live": True,
            "is_crypto": is_crypto(symbol),
        }
    else:
        base_price = _known_base_price(symbol)
        if base_price is None:
            return None  # never seen this symbol succeed and it's not in a curated list — treat as unknown
        price = _simulated_price(symbol, base_price)
        prev = _cache.get(symbol, {}).get("quote", {}).get("price", base_price)
        quote = {
            "symbol": symbol,
            "name": get_name(symbol),
            "price": price,
            "change": round(price - prev, 6 if price < 1 else 2),
            "percent_change": round(((price - prev) / prev) * 100, 2) if prev else 0.0,
            "live": False,
            "is_crypto": is_crypto(symbol),
        }

    _cache[symbol] = {"ts": time.time(), "quote": quote}
    return quote


def _get_quotes_parallel(symbols) -> list:
    app = current_app._get_current_object()

    def _fetch(symbol):
        with app.app_context():
            return get_quote(symbol)

    with ThreadPoolExecutor(max_workers=8) as executor:
        return list(executor.map(_fetch, symbols))


def get_all_quotes() -> list:
    return _get_quotes_parallel([s["symbol"] for s in STOCKS])


def get_all_crypto_quotes() -> list:
    return _get_quotes_parallel([c["symbol"] for c in CRYPTO])


def portfolio_net_worth(portfolio) -> float:
    total = portfolio.cash
    for holding in portfolio.holdings:
        quote = get_quote(holding.symbol)
        price = quote["price"] if quote else holding.avg_cost
        total += holding.quantity * price
    return round(total, 2)


def search_symbols(query: str, include_crypto: bool) -> list:
    query = (query or "").strip()
    if len(query) < 1:
        return []
    try:
        resp = requests.get(
            "https://query1.finance.yahoo.com/v1/finance/search",
            params={"q": query, "quotesCount": 12, "newsCount": 0},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5,
        )
        resp.raise_for_status()
        quotes = resp.json().get("quotes", [])
    except (requests.RequestException, KeyError, ValueError):
        quotes = []

    results = []
    for q in quotes:
        symbol = q.get("symbol", "")
        quote_type = q.get("quoteType", "")
        name = q.get("shortname") or q.get("longname") or symbol
        if quote_type == "CRYPTOCURRENCY":
            _dynamic_name.setdefault(symbol.upper(), name)
            results.append({"symbol": symbol, "name": name, "type": "crypto", "locked": not include_crypto})
        elif quote_type == "EQUITY":
            _dynamic_name.setdefault(symbol.upper(), name)
            results.append({"symbol": symbol, "name": name, "type": "stock", "locked": False})

    return results[:10]


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
            {"t": t, "price": round(c, 6 if c < 1 else 2)}
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
        points.append({"t": int(t), "price": round(max(price, 0.000001), 6 if price < 1 else 2)})
    return points


def get_history(symbol: str, range_key: str) -> dict:
    symbol = symbol.upper()
    if range_key not in HISTORY_RANGES:
        return None

    cache_key = f"{symbol}:{range_key}"
    cached = _history_cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < HISTORY_CACHE_TTL_SECONDS:
        return cached["data"]

    points = _fetch_real_history(symbol, range_key)
    live = points is not None
    if not points:
        base_price = _known_base_price(symbol)
        if base_price is None:
            return None
        points = _simulated_history(symbol, base_price, range_key)

    data = {"symbol": symbol, "range": range_key, "live": live, "points": points}
    _history_cache[cache_key] = {"ts": time.time(), "data": data}
    return data
