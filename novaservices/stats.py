"""Chiffres du tableau de bord, calculés sur les tickets visibles par l'utilisateur connecté."""

from datetime import timedelta

from flask import Blueprint, g, jsonify

from .auth import login_required
from .models import CATEGORIES, CLOSED_STATUSES, OPEN_STATUSES, PRIORITIES, STATUSES, Ticket, User, utcnow
from .tickets import visible_tickets

bp = Blueprint("stats", __name__, url_prefix="/api/stats")

DAYS = 14
# Ancienneté d'un ticket ouvert, en heures : [début, fin[
AGE_BUCKETS = [
    ("moins_1j", "Moins d'un jour", 0, 24),
    ("1_3j", "1 à 3 jours", 24, 72),
    ("3_7j", "3 à 7 jours", 72, 168),
    ("plus_7j", "Plus de 7 jours", 168, None),
]


@bp.get("")
@login_required
def stats():
    now = utcnow()
    today = now.date()
    tickets = visible_tickets().all()
    open_tickets = [t for t in tickets if t.status in OPEN_STATUSES]

    by_status = {s: 0 for s in STATUSES}
    for t in tickets:
        by_status[t.status] += 1

    # Créés et résolus par jour, sur les 14 derniers jours, aujourd'hui compris.
    first_day = today - timedelta(days=DAYS - 1)
    daily = {first_day + timedelta(days=i): {"created": 0, "resolved": 0} for i in range(DAYS)}
    for t in tickets:
        if t.created_at.date() in daily:
            daily[t.created_at.date()]["created"] += 1
        if t.resolved_at and t.resolved_at.date() in daily:
            daily[t.resolved_at.date()]["resolved"] += 1

    month_ago = now - timedelta(days=30)
    resolved_month = [t for t in tickets if t.resolved_at and t.resolved_at >= month_ago]
    avg_hours = (
        round(sum((t.resolved_at - t.created_at).total_seconds() for t in resolved_month) / 3600 / len(resolved_month), 1)
        if resolved_month
        else None
    )

    ages = []
    for key, label, low, high in AGE_BUCKETS:
        bucket = [
            t
            for t in open_tickets
            if (now - t.created_at).total_seconds() / 3600 >= low
            and (high is None or (now - t.created_at).total_seconds() / 3600 < high)
        ]
        bucket.sort(key=lambda t: t.created_at)
        ages.append(
            {
                "key": key,
                "label": label,
                "tickets": [
                    {"id": t.id, "title": t.title, "priority": t.priority, "assigned": t.assigned_to_id is not None}
                    for t in bucket
                ],
            }
        )

    week_ago = now - timedelta(days=7)
    unassigned = sorted((t for t in open_tickets if t.assigned_to_id is None), key=lambda t: t.created_at)
    data = {
        "generated_at": now.isoformat(timespec="seconds") + "Z",
        "total": len(tickets),
        "open": len(open_tickets),
        "unassigned": len(unassigned),
        "critical_open": sum(1 for t in open_tickets if t.priority == "critique"),
        "waiting_reply": by_status["en_attente"],
        "created_7d": sum(1 for t in tickets if t.created_at >= week_ago),
        "resolved_7d": sum(1 for t in tickets if t.resolved_at and t.resolved_at >= week_ago),
        "resolved_30d": len(resolved_month),
        "avg_resolution_hours": avg_hours,
        "by_status": by_status,
        "by_priority": {p: sum(1 for t in open_tickets if t.priority == p) for p in PRIORITIES},
        "by_category": {c: sum(1 for t in open_tickets if t.category == c) for c in CATEGORIES},
        "daily": [{"date": d.isoformat(), **v} for d, v in daily.items()],
        "ages": ages,
        "queue": [t.to_dict() for t in unassigned[:5]],
    }
    if g.user.is_admin:
        admins = User.query.filter_by(role="admin", active=True).order_by(User.name).all()
        data["workload"] = [
            {"id": a.id, "name": a.name, "open": sum(1 for t in open_tickets if t.assigned_to_id == a.id)}
            for a in admins
        ]
    else:
        # Pour un utilisateur : ses demandes actives, les plus récemment mises à jour d'abord.
        active = sorted(open_tickets, key=lambda t: t.updated_at, reverse=True)
        data["active"] = [t.to_dict() for t in active[:6]]
        data["recently_closed"] = [
            t.to_dict() for t in sorted((t for t in tickets if t.status in CLOSED_STATUSES), key=lambda t: t.resolved_at, reverse=True)[:3]
        ]
    return jsonify(data)
