"""NovaServices : helpdesk interne du support informatique."""

import logging
import os

from flask import Flask, jsonify, render_template, request

from . import auth, pages, stats, tickets, users
from .models import User, db, meta
from .seed import seed_demo

DEV_SECRET = "dev-secret-a-changer"


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True, static_folder="../static", template_folder="../templates")
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///novaservices.db"),
        JWT_SECRET=os.environ.get("JWT_SECRET", DEV_SECRET),
        JWT_EXPIRES_MINUTES=int(os.environ.get("JWT_EXPIRES_MINUTES", "480")),
        ADMIN_EMAIL=os.environ.get("ADMIN_EMAIL"),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD"),
        SEED_DEMO=os.environ.get("SEED_DEMO") == "1",
    )
    if config:
        app.config.update(config)
    if app.config["JWT_SECRET"] == DEV_SECRET:
        logging.getLogger(__name__).warning("JWT_SECRET n'est pas défini : secret de développement utilisé.")

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    for module in (auth, tickets, users, stats, pages):
        app.register_blueprint(module.bp)

    @app.context_processor
    def inject_meta():
        return {"meta": meta(), "demo": app.config["SEED_DEMO"]}

    @app.get("/health")
    def health():
        # FAIL_HEALTH=1 permet de simuler une panne au déploiement.
        if os.environ.get("FAIL_HEALTH") == "1":
            return jsonify(status="ko"), 503
        return jsonify(status="ok")

    @app.get("/version")
    def version():
        return jsonify(
            version=os.environ.get("APP_VERSION", "dev"),
            commit=os.environ.get("GIT_COMMIT", "local"),
        )

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
            return jsonify(erreur="Ressource introuvable."), 404
        return render_template("pages/404.html"), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify(erreur="Méthode non autorisée."), 405

    with app.app_context():
        db.create_all()
        ensure_admin(app)
        if app.config["SEED_DEMO"]:
            seed_demo()

    return app


def ensure_admin(app):
    """Crée le compte administrateur défini par ADMIN_EMAIL et ADMIN_PASSWORD s'il n'existe pas."""
    email, password = app.config["ADMIN_EMAIL"], app.config["ADMIN_PASSWORD"]
    if not email or not password or User.query.filter_by(email=email.lower()).first():
        return
    admin = User(email=email.lower(), name="Administrateur", service="Support informatique", role="admin")
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
