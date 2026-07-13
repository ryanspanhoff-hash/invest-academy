from flask import Blueprint, render_template, jsonify, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import LearningProgress
from app.learning import content

learning_bp = Blueprint("learning", __name__, template_folder="../templates/learning")


def _completed_ids():
    if not current_user.is_authenticated:
        return set()
    return {p.item_id for p in current_user.progress_items}


@learning_bp.route("/")
@login_required
def home():
    completed = _completed_ids()
    total = len(content.all_items_index())
    done = len(completed & set(content.all_items_index()))
    pct = round((done / total) * 100) if total else 0
    return render_template(
        "learning/home.html",
        videos=content.VIDEOS,
        articles=content.ARTICLES,
        tips=content.TIPS,
        completed=completed,
        pct=pct,
        done=done,
        total=total,
    )


@learning_bp.route("/article/<slug>")
@login_required
def article(slug):
    art = content.get_article(slug)
    if not art:
        abort(404)
    completed = _completed_ids()
    return render_template("learning/article.html", article=art, completed=completed)


@learning_bp.route("/complete/<item_id>", methods=["POST"])
@login_required
def complete(item_id):
    if item_id not in content.all_items_index():
        abort(404)
    exists = LearningProgress.query.filter_by(user_id=current_user.id, item_id=item_id).first()
    if not exists:
        db.session.add(LearningProgress(user_id=current_user.id, item_id=item_id))
        db.session.commit()
    return jsonify({"ok": True, "item_id": item_id})
