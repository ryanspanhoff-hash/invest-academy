from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from app.learning import content as learning_content
from app.practice import market
from app.practice.leveling import level_info_and_flash

main_bp = Blueprint("main", __name__, template_folder="../templates/main")


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("main/landing.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    portfolio = current_user.portfolio
    info = level_info_and_flash(portfolio)

    completed = {p.item_id for p in current_user.progress_items}
    total_learning = len(learning_content.all_items_index())
    learning_pct = round((len(completed) / total_learning) * 100) if total_learning else 0

    top_movers = sorted(market.get_all_quotes(), key=lambda q: abs(q["percent_change"]), reverse=True)[:4]

    return render_template(
        "main/dashboard.html",
        info=info,
        portfolio=portfolio,
        learning_pct=learning_pct,
        learning_done=len(completed),
        learning_total=total_learning,
        top_movers=top_movers,
        holdings_count=len([h for h in portfolio.holdings if h.quantity > 0]),
    )
