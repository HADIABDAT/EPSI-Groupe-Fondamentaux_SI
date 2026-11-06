"""Pages HTML. Elles chargent leurs données par l'API : le contrôle d'accès se fait côté API."""

from flask import Blueprint, render_template

bp = Blueprint("pages", __name__)


@bp.get("/")
def dashboard():
    return render_template("pages/dashboard.html", page="dashboard")


@bp.get("/connexion")
def login():
    return render_template("pages/login.html")


@bp.get("/inscription")
def register():
    return render_template("pages/register.html")


@bp.get("/tickets")
def tickets():
    return render_template("pages/tickets.html", page="tickets")


@bp.get("/tickets/nouveau")
def new_ticket():
    return render_template("pages/new_ticket.html", page="new")


@bp.get("/tickets/<int:ticket_id>")
def ticket(ticket_id):
    return render_template("pages/ticket.html", page="tickets", ticket_id=ticket_id)


@bp.get("/utilisateurs")
def users():
    return render_template("pages/users.html", page="users")


@bp.get("/compte")
def account():
    return render_template("pages/account.html", page="account")
