"""Authentification par JWT : inscription, connexion, profil."""

import re
from datetime import timedelta
from functools import wraps

import jwt
from flask import Blueprint, current_app, g, jsonify, request

from .models import User, db, utcnow

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8


def error(message, status):
    return jsonify(erreur=message), status


def create_token(user):
    now = utcnow()
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(minutes=current_app.config["JWT_EXPIRES_MINUTES"]),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")


def current_user_from_token():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None, "Connexion requise."
    try:
        payload = jwt.decode(header[7:], current_app.config["JWT_SECRET"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None, "Ta session a expiré. Reconnecte-toi."
    except jwt.InvalidTokenError:
        return None, "Jeton invalide."
    # Le rôle est relu en base à chaque requête : un changement de rôle s'applique tout de suite.
    user = db.session.get(User, int(payload["sub"]))
    if user is None or not user.active:
        return None, "Ce compte n'existe plus ou a été désactivé."
    return user, None


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        user, message = current_user_from_token()
        if user is None:
            return error(message, 401)
        g.user = user
        return view(*args, **kwargs)

    return wrapper


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if not g.user.is_admin:
            return error("Réservé aux administrateurs.", 403)
        return view(*args, **kwargs)

    return wrapper


def validate_profile(data, require_password=True):
    """Renvoie (champs nettoyés, erreurs par champ)."""
    errors = {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    service = str(data.get("service", "")).strip()
    if not 2 <= len(name) <= 120:
        errors["name"] = "Indique ton nom (2 caractères au moins)."
    if not EMAIL_RE.match(email):
        errors["email"] = "Cette adresse e-mail n'est pas valide."
    elif User.query.filter_by(email=email).first():
        errors["email"] = "Un compte existe déjà avec cette adresse."
    if require_password and len(password) < MIN_PASSWORD:
        errors["password"] = f"Le mot de passe doit faire {MIN_PASSWORD} caractères au moins."
    if len(service) > 80:
        errors["service"] = "80 caractères au plus."
    return {"name": name, "email": email, "password": password, "service": service}, errors


@bp.post("/register")
def register():
    fields, errors = validate_profile(request.get_json(silent=True) or {})
    if errors:
        return jsonify(erreur="Vérifie les champs du formulaire.", champs=errors), 400
    user = User(name=fields["name"], email=fields["email"], service=fields["service"], role="user")
    user.set_password(fields["password"])
    db.session.add(user)
    db.session.commit()
    return jsonify(token=create_token(user), user=user.to_dict()), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(str(data.get("password", ""))):
        return error("Adresse e-mail ou mot de passe incorrect.", 401)
    if not user.active:
        return error("Ce compte a été désactivé. Contacte le support.", 403)
    return jsonify(token=create_token(user), user=user.to_dict())


@bp.get("/me")
@login_required
def me():
    return jsonify(g.user.to_dict())


@bp.patch("/me")
@login_required
def update_me():
    data = request.get_json(silent=True) or {}
    errors = {}
    if "name" in data:
        name = str(data["name"]).strip()
        if not 2 <= len(name) <= 120:
            errors["name"] = "Indique ton nom (2 caractères au moins)."
        else:
            g.user.name = name
    if "service" in data:
        service = str(data["service"]).strip()
        if len(service) > 80:
            errors["service"] = "80 caractères au plus."
        else:
            g.user.service = service
    if errors:
        db.session.rollback()
        return jsonify(erreur="Vérifie les champs du formulaire.", champs=errors), 400
    db.session.commit()
    return jsonify(g.user.to_dict())


@bp.post("/me/password")
@login_required
def change_password():
    data = request.get_json(silent=True) or {}
    if not g.user.check_password(str(data.get("current", ""))):
        return jsonify(erreur="Le mot de passe actuel est incorrect.", champs={"current": "Mot de passe incorrect."}), 400
    new = str(data.get("new", ""))
    if len(new) < MIN_PASSWORD:
        message = f"Le mot de passe doit faire {MIN_PASSWORD} caractères au moins."
        return jsonify(erreur=message, champs={"new": message}), 400
    g.user.set_password(new)
    db.session.commit()
    return jsonify(message="Mot de passe modifié.")
