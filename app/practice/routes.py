from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Holding, Transaction
from app.practice import market
from app.practice.leveling import level_info_and_flash

practice_bp = Blueprint("practice", __name__, template_folder="../templates/practice")


@practice_bp.route("/")
@login_required
def home():
    portfolio = current_user.portfolio
    quotes = market.get_all_quotes()
    net_worth = market.portfolio_net_worth(portfolio)
    info = level_info_and_flash(portfolio, net_worth=net_worth)

    holdings_view = []
    for h in portfolio.holdings:
        if h.quantity <= 0:
            continue
        quote = next((q for q in quotes if q["symbol"] == h.symbol), None)
        current_price = quote["price"] if quote else h.avg_cost
        market_value = round(h.quantity * current_price, 2)
        cost_basis = round(h.quantity * h.avg_cost, 2)
        gain = round(market_value - cost_basis, 2)
        gain_pct = round((gain / cost_basis) * 100, 2) if cost_basis else 0.0
        holdings_view.append({
            "symbol": h.symbol,
            "name": market.STOCK_LOOKUP.get(h.symbol, {}).get("name", h.symbol),
            "quantity": h.quantity,
            "avg_cost": h.avg_cost,
            "current_price": current_price,
            "market_value": market_value,
            "gain": gain,
            "gain_pct": gain_pct,
        })

    return render_template(
        "practice/home.html",
        quotes=quotes,
        portfolio=portfolio,
        holdings=holdings_view,
        info=info,
        has_api_key=bool(current_app.config.get("FINNHUB_API_KEY")),
    )


@practice_bp.route("/buy", methods=["POST"])
@login_required
def buy():
    portfolio = current_user.portfolio
    symbol = request.form.get("symbol", "").upper()
    try:
        quantity = float(request.form.get("quantity", 0))
    except ValueError:
        quantity = 0

    quote = market.get_quote(symbol)
    if not quote:
        flash("Unknown stock symbol.", "error")
        return redirect(url_for("practice.home"))

    if quantity <= 0:
        flash("Enter a quantity greater than zero.", "error")
        return redirect(url_for("practice.home"))

    cost = round(quantity * quote["price"], 2)
    if cost > portfolio.cash:
        flash(f"Not enough cash. That trade costs ${cost:,.2f} but you have ${portfolio.cash:,.2f}.", "error")
        return redirect(url_for("practice.home"))

    holding = Holding.query.filter_by(portfolio_id=portfolio.id, symbol=symbol).first()
    if holding:
        total_cost = holding.avg_cost * holding.quantity + cost
        holding.quantity += quantity
        holding.avg_cost = round(total_cost / holding.quantity, 4)
    else:
        holding = Holding(portfolio_id=portfolio.id, symbol=symbol, quantity=quantity, avg_cost=quote["price"])
        db.session.add(holding)

    portfolio.cash = round(portfolio.cash - cost, 2)
    db.session.add(Transaction(
        portfolio_id=portfolio.id, symbol=symbol, side="BUY",
        quantity=quantity, price=quote["price"], total=cost,
    ))
    db.session.commit()

    flash(f"Bought {quantity:g} shares of {symbol} at ${quote['price']:,.2f}.", "success")
    level_info_and_flash(portfolio)
    return redirect(url_for("practice.home"))


@practice_bp.route("/sell", methods=["POST"])
@login_required
def sell():
    portfolio = current_user.portfolio
    symbol = request.form.get("symbol", "").upper()
    try:
        quantity = float(request.form.get("quantity", 0))
    except ValueError:
        quantity = 0

    holding = Holding.query.filter_by(portfolio_id=portfolio.id, symbol=symbol).first()
    if not holding or quantity <= 0 or quantity > holding.quantity:
        flash("You don't own that many shares to sell.", "error")
        return redirect(url_for("practice.home"))

    quote = market.get_quote(symbol)
    proceeds = round(quantity * quote["price"], 2)
    realized_pl = round((quote["price"] - holding.avg_cost) * quantity, 2)

    holding.quantity -= quantity
    if holding.quantity <= 0.0001:
        db.session.delete(holding)

    portfolio.cash = round(portfolio.cash + proceeds, 2)
    db.session.add(Transaction(
        portfolio_id=portfolio.id, symbol=symbol, side="SELL",
        quantity=quantity, price=quote["price"], total=proceeds, realized_pl=realized_pl,
    ))
    db.session.commit()

    pl_word = "profit" if realized_pl >= 0 else "loss"
    flash(f"Sold {quantity:g} shares of {symbol} at ${quote['price']:,.2f} ({pl_word} of ${abs(realized_pl):,.2f}).",
          "success")
    level_info_and_flash(portfolio)
    return redirect(url_for("practice.home"))


@practice_bp.route("/history")
@login_required
def history():
    portfolio = current_user.portfolio
    return render_template("practice/history.html", transactions=portfolio.transactions, portfolio=portfolio)


@practice_bp.route("/progress")
@login_required
def progress():
    portfolio = current_user.portfolio
    info = level_info_and_flash(portfolio)
    return render_template("practice/progress.html", info=info, portfolio=portfolio)


@practice_bp.route("/api/quotes")
@login_required
def api_quotes():
    return jsonify(market.get_all_quotes())
