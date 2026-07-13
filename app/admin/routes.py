from collections import defaultdict
from functools import wraps

from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from app.models import User, Transaction
from app.learning import content as learning_content
from app.practice import market
from app.practice.leveling import level_info

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(404)
        return f(*args, **kwargs)
    return wrapper


@admin_bp.route("/")
@admin_required
def dashboard():
    users = User.query.order_by(User.created_at).all()
    total_users = len(users)
    total_items = len(learning_content.all_items_index())

    total_net_worth = 0.0
    total_growth = 0.0
    level_counts = defaultdict(int)
    performers = []

    for u in users:
        p = u.portfolio
        if not p:
            continue
        net_worth = market.portfolio_net_worth(p)
        growth = round(net_worth - p.starting_balance, 2)
        info = level_info(p, net_worth=net_worth)

        total_net_worth += net_worth
        total_growth += growth
        level_counts[info["highest_level"]] += 1

        done = len(u.progress_items)
        pct = round((done / total_items) * 100) if total_items else 0

        performers.append({
            "username": u.username,
            "level": info["current_level"],
            "icon": info["current_icon"],
            "net_worth": net_worth,
            "growth": growth,
            "learning_pct": pct,
            "joined": u.created_at,
        })

    performers.sort(key=lambda x: x["growth"], reverse=True)
    top_performers = performers[:10]
    recent_signups = sorted(performers, key=lambda x: x["joined"], reverse=True)[:10]

    avg_learning_pct = round(sum(p["learning_pct"] for p in performers) / len(performers)) if performers else 0
    avg_growth = round(total_growth / total_users, 2) if total_users else 0

    signups_by_day = defaultdict(int)
    for u in users:
        day = (u.created_at or u.portfolio.created_at).strftime("%Y-%m-%d") if u.created_at else "unknown"
        signups_by_day[day] += 1
    sorted_days = sorted(signups_by_day.keys())
    cumulative = 0
    signup_series = []
    for day in sorted_days:
        cumulative += signups_by_day[day]
        signup_series.append({"day": day, "count": signups_by_day[day], "cumulative": cumulative})

    max_level = max(level_counts.keys()) if level_counts else 1
    level_chart = [
        {"level": lvl, "label": f"Lvl {lvl}", "count": level_counts.get(lvl, 0)}
        for lvl in range(1, max_level + 1)
    ]

    total_trades = Transaction.query.count()
    buy_count = Transaction.query.filter_by(side="BUY").count()
    sell_count = Transaction.query.filter_by(side="SELL").count()

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_net_worth=round(total_net_worth, 2),
        total_growth=round(total_growth, 2),
        avg_growth=avg_growth,
        avg_learning_pct=avg_learning_pct,
        total_trades=total_trades,
        buy_count=buy_count,
        sell_count=sell_count,
        signup_series=signup_series,
        level_chart=level_chart,
        top_performers=top_performers,
        recent_signups=recent_signups,
    )
