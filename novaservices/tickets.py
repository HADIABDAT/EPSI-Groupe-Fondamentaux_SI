"""API des tickets : liste, création, détail, mise à jour, commentaires."""

from flask import Blueprint, g, jsonify, request
from sqlalchemy import case, or_

from .auth import admin_required, error, login_required
from .models import (
    CATEGORIES,
    CLOSED_STATUSES,
    OPEN_STATUSES,
    PRIORITIES,
    STATUSES,
    Comment,
    Event,
    Ticket,
    User,
    db,
    utcnow,
)

bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")

MAX_PER_PAGE = 100
PRIORITY_ORDER = case({"critique": 0, "haute": 1, "normale": 2, "basse": 3}, value=Ticket.priority)
SORTS = {
    "recent": (Ticket.updated_at.desc(),),
    "ancien": (Ticket.created_at.asc(),),
    "priorite": (PRIORITY_ORDER, Ticket.created_at.asc()),
}


def visible_tickets():
    """Un administrateur voit tout ; un utilisateur ne voit que ses propres demandes."""
    query = Ticket.query
    if not g.user.is_admin:
        query = query.filter(Ticket.created_by_id == g.user.id)
    return query


def get_visible_ticket(ticket_id):
    # Un ticket d'un autre utilisateur renvoie 404, pas 403 : on ne révèle pas qu'il existe.
    return visible_tickets().filter(Ticket.id == ticket_id).first()


def int_arg(name, default, minimum=1, maximum=None):
    try:
        value = int(request.args.get(name, default))
    except ValueError:
        return default
    value = max(value, minimum)
    return min(value, maximum) if maximum else value


def log(ticket, kind, old=None, new=None):
    ticket.events.append(Event(actor_id=g.user.id, kind=kind, old_value=old, new_value=new))


def set_status(ticket, status):
    if status == ticket.status:
        return
    log(ticket, "status", ticket.status, status)
    ticket.status = status
    if status in CLOSED_STATUSES:
        ticket.resolved_at = ticket.resolved_at or utcnow()
    else:
        ticket.resolved_at = None


@bp.get("")
@login_required
def list_tickets():
    query = visible_tickets()
    for field, choices in (("status", STATUSES), ("priority", PRIORITIES), ("category", CATEGORIES)):
        value = request.args.get(field)
        if value == "actifs" and field == "status":
            query = query.filter(Ticket.status.in_(OPEN_STATUSES))
        elif value in choices:
            query = query.filter(getattr(Ticket, field) == value)
    assigned = request.args.get("assigned")
    if assigned == "moi":
        query = query.filter(Ticket.assigned_to_id == g.user.id)
    elif assigned == "aucun":
        query = query.filter(Ticket.assigned_to_id.is_(None))
    elif assigned and assigned.isdigit():
        query = query.filter(Ticket.assigned_to_id == int(assigned))
    search = request.args.get("q", "").strip()
    if search:
        pattern = f"%{search}%"
        conditions = [Ticket.title.ilike(pattern), Ticket.description.ilike(pattern)]
        if search.lstrip("#").isdigit():
            conditions.append(Ticket.id == int(search.lstrip("#")))
        query = query.filter(or_(*conditions))

    total = query.count()
    per_page = int_arg("per_page", 20, maximum=MAX_PER_PAGE)
    pages = max(1, -(-total // per_page))
    page = int_arg("page", 1, maximum=pages)
    order = SORTS.get(request.args.get("sort"), SORTS["recent"])
    items = query.order_by(*order, Ticket.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return jsonify(items=[t.to_dict() for t in items], total=total, page=page, pages=pages, per_page=per_page)


@bp.get("/counts")
@login_required
def counts():
    """Nombre de tickets visibles par statut, pour les filtres de la liste."""
    rows = visible_tickets().with_entities(Ticket.status, db.func.count()).group_by(Ticket.status).all()
    by_status = {status: 0 for status in STATUSES}
    by_status.update(dict(rows))
    return jsonify(by_status)


@bp.post("")
@login_required
def create_ticket():
    data = request.get_json(silent=True) or {}
    errors = {}
    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    category = data.get("category", "autre")
    priority = data.get("priority", "normale")
    if not 5 <= len(title) <= 120:
        errors["title"] = "Le sujet doit faire entre 5 et 120 caractères."
    if not 10 <= len(description) <= 5000:
        errors["description"] = "Décris le problème en 10 caractères au moins."
    if category not in CATEGORIES:
        errors["category"] = "Choisis une catégorie de la liste."
    if priority not in PRIORITIES:
        errors["priority"] = "Choisis une priorité de la liste."
    if errors:
        return jsonify(erreur="Vérifie les champs du formulaire.", champs=errors), 400
    ticket = Ticket(
        title=title, description=description, category=category, priority=priority, created_by_id=g.user.id
    )
    db.session.add(ticket)
    log(ticket, "created")
    db.session.commit()
    return jsonify(ticket.to_dict(full=True)), 201


@bp.get("/<int:ticket_id>")
@login_required
def get_ticket(ticket_id):
    ticket = get_visible_ticket(ticket_id)
    if ticket is None:
        return error("Ce ticket n'existe pas.", 404)
    return jsonify(ticket.to_dict(full=True))


@bp.patch("/<int:ticket_id>")
@login_required
def update_ticket(ticket_id):
    ticket = get_visible_ticket(ticket_id)
    if ticket is None:
        return error("Ce ticket n'existe pas.", 404)
    data = request.get_json(silent=True) or {}

    if not g.user.is_admin:
        # Le demandeur peut seulement fermer sa demande, ou la rouvrir si elle est résolue.
        if set(data) - {"status"}:
            return error("Seul le support peut modifier ces champs.", 403)
        status = data.get("status")
        allowed = status == "ferme" or (status == "ouvert" and ticket.status == "resolu")
        if not allowed:
            return error("Tu peux fermer ta demande, ou la rouvrir quand elle est résolue.", 403)
        set_status(ticket, status)
    else:
        errors = {}
        if "status" in data and data["status"] not in STATUSES:
            errors["status"] = "Statut inconnu."
        if "priority" in data and data["priority"] not in PRIORITIES:
            errors["priority"] = "Priorité inconnue."
        if "category" in data and data["category"] not in CATEGORIES:
            errors["category"] = "Catégorie inconnue."
        assignee = None
        if data.get("assigned_to_id") is not None:
            assignee = db.session.get(User, data["assigned_to_id"]) if isinstance(data["assigned_to_id"], int) else None
            if assignee is None or not assignee.is_admin or not assignee.active:
                errors["assigned_to_id"] = "On ne peut assigner un ticket qu'à un administrateur actif."
        if errors:
            return jsonify(erreur="Vérifie les champs.", champs=errors), 400

        if "assigned_to_id" in data and data["assigned_to_id"] != ticket.assigned_to_id:
            old = ticket.assigned_to.name if ticket.assigned_to else None
            log(ticket, "assigned", old, assignee.name if assignee else None)
            ticket.assigned_to = assignee
            # Prendre un ticket ouvert le passe en cours.
            if assignee and ticket.status == "ouvert" and "status" not in data:
                set_status(ticket, "en_cours")
        if "priority" in data and data["priority"] != ticket.priority:
            log(ticket, "priority", ticket.priority, data["priority"])
            ticket.priority = data["priority"]
        if "category" in data and data["category"] != ticket.category:
            log(ticket, "category", ticket.category, data["category"])
            ticket.category = data["category"]
        if "status" in data:
            set_status(ticket, data["status"])

    ticket.updated_at = utcnow()
    db.session.commit()
    return jsonify(ticket.to_dict(full=True))


@bp.delete("/<int:ticket_id>")
@admin_required
def delete_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if ticket is None:
        return error("Ce ticket n'existe pas.", 404)
    db.session.delete(ticket)
    db.session.commit()
    return "", 204


@bp.post("/<int:ticket_id>/comments")
@login_required
def add_comment(ticket_id):
    ticket = get_visible_ticket(ticket_id)
    if ticket is None:
        return error("Ce ticket n'existe pas.", 404)
    body = str((request.get_json(silent=True) or {}).get("body", "")).strip()
    if not 1 <= len(body) <= 5000:
        return jsonify(erreur="Écris un message (5 000 caractères au plus).", champs={"body": "Message vide."}), 400
    if ticket.status == "ferme":
        return error("Ce ticket est fermé. Ouvre une nouvelle demande.", 409)
    ticket.comments.append(Comment(author_id=g.user.id, body=body))
    # La réponse du demandeur relance un ticket qui l'attendait.
    if not g.user.is_admin and ticket.status == "en_attente":
        set_status(ticket, "en_cours")
    ticket.updated_at = utcnow()
    db.session.commit()
    return jsonify(ticket.to_dict(full=True)), 201
