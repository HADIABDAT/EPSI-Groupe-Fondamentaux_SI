"""Gestion des comptes, réservée aux administrateurs."""

from flask import Blueprint, g, jsonify, request
from sqlalchemy import or_

from .auth import admin_required, error, validate_profile
from .models import OPEN_STATUSES, ROLES, Ticket, User, db

bp = Blueprint("users", __name__, url_prefix="/api/users")


def with_counts(users):
    """Ajoute à chaque compte ses demandes ouvertes et, pour le support, les tickets qui lui sont assignés."""
    ids = [u.id for u in users]
    opened = dict(
        db.session.query(Ticket.created_by_id, db.func.count())
        .filter(Ticket.created_by_id.in_(ids), Ticket.status.in_(OPEN_STATUSES))
        .group_by(Ticket.created_by_id)
    )
    assigned = dict(
        db.session.query(Ticket.assigned_to_id, db.func.count())
        .filter(Ticket.assigned_to_id.in_(ids), Ticket.status.in_(OPEN_STATUSES))
        .group_by(Ticket.assigned_to_id)
    )
    return [u.to_dict() | {"open_requests": opened.get(u.id, 0), "open_assigned": assigned.get(u.id, 0)} for u in users]


@bp.get("")
@admin_required
def list_users():
    query = User.query
    role = request.args.get("role")
    if role in ROLES:
        query = query.filter(User.role == role)
    if request.args.get("active") == "1":
        query = query.filter(User.active.is_(True))
    search = request.args.get("q", "").strip()
    if search:
        pattern = f"%{search}%"
        query = query.filter(or_(User.name.ilike(pattern), User.email.ilike(pattern), User.service.ilike(pattern)))
    return jsonify(with_counts(query.order_by(User.name).all()))


@bp.post("")
@admin_required
def create_user():
    data = request.get_json(silent=True) or {}
    fields, errors = validate_profile(data)
    role = data.get("role", "user")
    if role not in ROLES:
        errors["role"] = "Rôle inconnu."
    if errors:
        return jsonify(erreur="Vérifie les champs du formulaire.", champs=errors), 400
    user = User(name=fields["name"], email=fields["email"], service=fields["service"], role=role)
    user.set_password(fields["password"])
    db.session.add(user)
    db.session.commit()
    return jsonify(with_counts([user])[0]), 201


@bp.patch("/<int:user_id>")
@admin_required
def update_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return error("Ce compte n'existe pas.", 404)
    data = request.get_json(silent=True) or {}
    if user.id == g.user.id and (data.get("role", "admin") != "admin" or data.get("active", True) is False):
        return error("Tu ne peux pas retirer tes propres droits ni désactiver ton compte.", 400)
    if "role" in data:
        if data["role"] not in ROLES:
            return jsonify(erreur="Rôle inconnu.", champs={"role": "Rôle inconnu."}), 400
        user.role = data["role"]
        if user.role != "admin":
            # Un utilisateur ne garde pas de tickets assignés.
            Ticket.query.filter_by(assigned_to_id=user.id).update({"assigned_to_id": None})
    if "active" in data:
        user.active = bool(data["active"])
    if "service" in data:
        user.service = str(data["service"]).strip()[:80]
    db.session.commit()
    return jsonify(with_counts([user])[0])
