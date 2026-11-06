"""Modèles de données : utilisateurs, tickets, commentaires et historique."""

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

ROLES = {"user": "Utilisateur", "admin": "Administrateur"}
STATUSES = {
    "ouvert": "Ouvert",
    "en_cours": "En cours",
    "en_attente": "En attente de réponse",
    "resolu": "Résolu",
    "ferme": "Fermé",
}
OPEN_STATUSES = ("ouvert", "en_cours", "en_attente")
CLOSED_STATUSES = ("resolu", "ferme")
PRIORITIES = {"basse": "Basse", "normale": "Normale", "haute": "Haute", "critique": "Critique"}
CATEGORIES = {
    "materiel": "Matériel",
    "logiciel": "Logiciel",
    "reseau": "Réseau",
    "acces": "Accès et comptes",
    "messagerie": "Messagerie",
    "autre": "Autre",
}


def utcnow():
    # Stocké sans fuseau (SQLite n'en garde pas), toujours en UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(value):
    return value.isoformat(timespec="seconds") + "Z" if value else None


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    service = db.Column(db.String(80), nullable=False, default="")
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="user")
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "service": self.service,
            "role": self.role,
            "active": self.active,
            "created_at": iso(self.created_at),
        }

    def to_ref(self):
        return {"id": self.id, "name": self.name} if self else None


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(20), nullable=False, default="autre")
    priority = db.Column(db.String(10), nullable=False, default="normale")
    status = db.Column(db.String(12), nullable=False, default="ouvert", index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    resolved_at = db.Column(db.DateTime)

    created_by = db.relationship("User", foreign_keys=[created_by_id])
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])
    comments = db.relationship(
        "Comment", backref="ticket", cascade="all, delete-orphan", order_by="Comment.created_at"
    )
    events = db.relationship(
        "Event", backref="ticket", cascade="all, delete-orphan", order_by="Event.created_at"
    )

    def to_dict(self, full=False):
        data = {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "priority": self.priority,
            "status": self.status,
            "created_by": self.created_by.to_ref(),
            "assigned_to": self.assigned_to.to_ref() if self.assigned_to else None,
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
            "resolved_at": iso(self.resolved_at),
            "comment_count": len(self.comments),
        }
        if full:
            data["description"] = self.description
            data["comments"] = [c.to_dict() for c in self.comments]
            data["events"] = [e.to_dict() for e in self.events]
        return data


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("ticket.id"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    author = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "author": self.author.to_ref(),
            "author_role": self.author.role,
            "body": self.body,
            "created_at": iso(self.created_at),
        }


class Event(db.Model):
    """Une ligne d'historique : création, changement de statut, de priorité, d'assignation."""

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("ticket.id"), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    kind = db.Column(db.String(20), nullable=False)
    old_value = db.Column(db.String(120))
    new_value = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    actor = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "actor": self.actor.to_ref(),
            "kind": self.kind,
            "old": self.old_value,
            "new": self.new_value,
            "created_at": iso(self.created_at),
        }


def meta():
    """Les listes de choix et leurs libellés, partagées avec le frontend."""
    return {
        "roles": ROLES,
        "statuses": STATUSES,
        "open_statuses": list(OPEN_STATUSES),
        "priorities": PRIORITIES,
        "categories": CATEGORIES,
    }
