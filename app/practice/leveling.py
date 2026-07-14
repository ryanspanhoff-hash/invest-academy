import json
from datetime import datetime

from flask import flash, url_for

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
        new_level = info["highest_level"]
        flash(
            json.dumps({
                "level": new_level,
                "icon": badge_icon(new_level),
                "name": badge_name(new_level),
            }),
            "levelup",
        )
        _send_level_up_email(portfolio, new_level, info["net_worth"])
    return info


def _send_level_up_email(portfolio, new_level: int, net_worth: float):
    """Emails a congrats note with a recap of everything traded during the level
    just completed. Best-effort: any failure here is logged, never raised —
    a slow or broken email provider must never break a trade or a page load."""
    from app.models import Transaction
    from app.services.email import send_email

    try:
        user = portfolio.user
        level_start = portfolio.level_started_at or portfolio.created_at
        trades = (
            Transaction.query
            .filter(Transaction.portfolio_id == portfolio.id, Transaction.timestamp >= level_start)
            .order_by(Transaction.timestamp.asc())
            .all()
        )

        if trades:
            rows = "".join(
                f"""<tr>
                  <td style="padding:8px 10px;border-bottom:1px solid #e6ebf1;font-weight:600;">{t.symbol}</td>
                  <td style="padding:8px 10px;border-bottom:1px solid #e6ebf1;color:{'#16a34a' if t.side == 'BUY' else '#e0503a'};font-weight:600;">{t.side}</td>
                  <td style="padding:8px 10px;border-bottom:1px solid #e6ebf1;">{t.quantity:g}</td>
                  <td style="padding:8px 10px;border-bottom:1px solid #e6ebf1;">${t.price:,.2f}</td>
                  <td style="padding:8px 10px;border-bottom:1px solid #e6ebf1;">${t.total:,.2f}</td>
                  <td style="padding:8px 10px;border-bottom:1px solid #e6ebf1;">{'—' if t.side == 'BUY' else ('+${:.2f}'.format(t.realized_pl) if t.realized_pl >= 0 else '-${:.2f}'.format(abs(t.realized_pl)))}</td>
                </tr>"""
                for t in trades
            )
            realized_total = sum(t.realized_pl or 0 for t in trades if t.side == "SELL")
            summary = f"You made <strong>{len(trades)}</strong> trade{'s' if len(trades) != 1 else ''} this level"
            if any(t.side == "SELL" for t in trades):
                summary += f", with <strong>${realized_total:,.2f}</strong> in realized profit/loss from sells"
            summary += "."
            trades_html = f"""
              <p style="color:#5b6b7f;font-size:14px;">{summary}</p>
              <table style="width:100%;border-collapse:collapse;font-size:13px;margin-top:8px;">
                <thead>
                  <tr style="text-align:left;color:#5b6b7f;font-size:12px;text-transform:uppercase;">
                    <th style="padding:8px 10px;border-bottom:2px solid #e6ebf1;">Symbol</th>
                    <th style="padding:8px 10px;border-bottom:2px solid #e6ebf1;">Side</th>
                    <th style="padding:8px 10px;border-bottom:2px solid #e6ebf1;">Qty</th>
                    <th style="padding:8px 10px;border-bottom:2px solid #e6ebf1;">Price</th>
                    <th style="padding:8px 10px;border-bottom:2px solid #e6ebf1;">Total</th>
                    <th style="padding:8px 10px;border-bottom:2px solid #e6ebf1;">Realized P/L</th>
                  </tr>
                </thead>
                <tbody>{rows}</tbody>
              </table>
            """
        else:
            trades_html = (
                '<p style="color:#5b6b7f;font-size:14px;">You didn\'t make any trades this level — '
                "your portfolio grew from price movement alone. Nice patience!</p>"
            )

        try:
            progress_url = url_for("practice.progress", _external=True)
        except RuntimeError:
            progress_url = "/"

        html = f"""
        <div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:0 auto;">
          <div style="background:#0f1b2d;padding:28px 24px;text-align:center;border-radius:16px 16px 0 0;">
            <div style="font-size:36px;">{badge_icon(new_level)}</div>
            <h1 style="color:#fff;font-size:22px;margin:8px 0 0;font-family:Arial,sans-serif;">
              Level {new_level} — {badge_name(new_level)}!
            </h1>
          </div>
          <div style="background:#ffffff;padding:28px 24px;border:1px solid #e6ebf1;border-top:none;border-radius:0 0 16px 16px;">
            <p style="font-size:15px;color:#14202f;">Hey {user.username},</p>
            <p style="font-size:15px;color:#14202f;">
              Congrats — your practice portfolio just leveled up! Your net worth is now
              <strong>${net_worth:,.2f}</strong>.
            </p>
            <h3 style="font-size:16px;color:#14202f;margin-top:24px;">Recap: what you traded this level</h3>
            {trades_html}
            <p style="margin-top:28px;">
              <a href="{progress_url}" style="background:#16a34a;color:#fff;padding:12px 22px;border-radius:999px;
                text-decoration:none;font-weight:600;font-size:14px;display:inline-block;">
                View Your Progress
              </a>
            </p>
            <p style="font-size:12px;color:#5b6b7f;margin-top:24px;">
              Invest Academy — practice investing with $0 real risk. This is simulated trading, not real financial advice.
            </p>
          </div>
        </div>
        """

        send_email(
            to=user.email,
            subject=f"🎉 You reached Level {new_level}: {badge_name(new_level)}!",
            html=html,
        )
    except Exception as e:  # noqa: BLE001 — email is a nice-to-have, never worth breaking a trade over
        try:
            from flask import current_app
            current_app.logger.warning("Level-up email failed: %s", e)
        except RuntimeError:
            pass
    finally:
        portfolio.level_started_at = datetime.utcnow()
        db.session.commit()
