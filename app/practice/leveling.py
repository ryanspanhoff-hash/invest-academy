from flask import flash

from app.extensions import db

STARTING_BALANCE = 1000.0
CRYPTO_UNLOCK_LEVEL = 5


def level_step(level: int) -> float:
    """Dollar growth needed to go from `level` to `level + 1`: 100, 150, 200, 250, …"""
    return 100.0 + (level - 1) * 50.0


def _level_breakdown(growth: float):
    """Walks the increasing per-level thresholds to find (level, growth_at_level_floor)."""
    level = 1
    floor_growth = 0.0
    while growth - floor_growth >= level_step(level):
        floor_growth += level_step(level)
        level += 1
    return level, floor_growth


def crypto_unlocked(portfolio) -> bool:
    return portfolio.highest_level >= CRYPTO_UNLOCK_LEVEL


BADGE_NAMES = {
    1: "Rookie Investor",
    2: "Bull Runner",
    3: "Portfolio Builder",
    4: "Market Strategist",
    5: "Wealth Architect",
    6: "Investment Guru",
    7: "Wall Street Wizard",
    8: "Capital Commander",
    9: "Money Maverick",
    10: "Legendary Investor",
}

BADGE_ICONS = {
    1: "🌱",
    2: "🐂",
    3: "🧱",
    4: "🧭",
    5: "🏛️",
    6: "🎓",
    7: "🧙",
    8: "🚀",
    9: "💎",
    10: "👑",
}


def badge_name(level: int) -> str:
    if level in BADGE_NAMES:
        return BADGE_NAMES[level]
    return f"Legendary Investor Tier {level - 9}"


def badge_icon(level: int) -> str:
    if level in BADGE_ICONS:
        return BADGE_ICONS[level]
    return "👑"


def level_for_net_worth(net_worth: float) -> int:
    growth = max(0.0, net_worth - STARTING_BALANCE)
    level, _ = _level_breakdown(growth)
    return level


def level_info(portfolio, net_worth: float = None):
    """Returns a dict describing current level, progress, and badge case for a portfolio."""
    if net_worth is None:
        from app.practice.market import portfolio_net_worth
        net_worth = portfolio_net_worth(portfolio)

    growth = max(0.0, net_worth - STARTING_BALANCE)
    current_level, level_floor_growth = _level_breakdown(growth)

    if current_level > portfolio.highest_level:
        portfolio.highest_level = current_level
        db.session.commit()

    current_step = level_step(current_level)
    progress_into_level = growth - level_floor_growth
    progress_pct = min(100.0, max(0.0, (progress_into_level / current_step) * 100))

    next_level = current_level + 1
    amount_to_next = max(0.0, current_step - progress_into_level)

    earned_badges = [
        {"level": lvl, "name": badge_name(lvl), "icon": badge_icon(lvl)}
        for lvl in range(1, portfolio.highest_level + 1)
    ]

    return {
        "net_worth": net_worth,
        "growth": net_worth - STARTING_BALANCE,
        "current_level": current_level,
        "current_badge": badge_name(current_level),
        "current_icon": badge_icon(current_level),
        "next_level": next_level,
        "next_badge": badge_name(next_level),
        "next_icon": badge_icon(next_level),
        "progress_pct": progress_pct,
        "amount_to_next": amount_to_next,
        "highest_level": portfolio.highest_level,
        "earned_badges": earned_badges,
    }


def level_info_and_flash(portfolio, net_worth: float = None):
    """Like level_info, but also flashes a one-time celebration the moment a new
    all-time-high level is discovered — whether that happened because of a trade
    just now, or because the market simply drifted since the last page view."""
    level_before = portfolio.highest_level
    info = level_info(portfolio, net_worth=net_worth)
    if info["highest_level"] > level_before:
        flash(
            f"LEVEL UP! You're now Level {info['highest_level']}: "
            f"{badge_icon(info['highest_level'])} {badge_name(info['highest_level'])}",
            "levelup",
        )
    return info
