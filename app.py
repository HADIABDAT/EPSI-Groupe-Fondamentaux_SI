"""API de tickets informatiques NovaServices (TP CI/CD)."""

import os

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, render_template, request

# Charge .env sans écraser les variables déjà définies (celles injectées par Docker et le pipeline priment).
load_dotenv()

VALID_PRIORITIES = {"basse", "normale", "haute"}


def create_app():
    app = Flask(__name__)

    # Données fictives, en mémoire : réinitialisées à chaque démarrage.
    tickets = [
        {"id": 1, "titre": "Imprimante du 2e étage hors ligne", "priorite": "normale", "statut": "ouvert"},
        {"id": 2, "titre": "Accès VPN refusé", "priorite": "haute", "statut": "en_cours"},
        {"id": 3, "titre": "Demande de nouvel écran", "priorite": "basse", "statut": "ferme"},
    ]

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        # FAIL_HEALTH=1 permet de simuler une panne au déploiement (étape 13).
        if os.environ.get("FAIL_HEALTH") == "1":
            return jsonify(status="ko"), 503
        return jsonify(status="ok")

    @app.get("/version")
    def version():
        return jsonify(
            version=os.environ.get("APP_VERSION", "dev"),
            commit=os.environ.get("GIT_COMMIT", "local"),
        )

    @app.get("/tickets")
    def list_tickets():
        statut = request.args.get("statut")
        if statut:
            return jsonify([t for t in tickets if t["statut"] == statut])
        return jsonify(tickets)

    @app.get("/tickets/<int:ticket_id>")
    def get_ticket(ticket_id):
        for ticket in tickets:
            if ticket["id"] == ticket_id:
                return jsonify(ticket)
        abort(404)

    @app.post("/tickets")
    def create_ticket():
        data = request.get_json(silent=True) or {}
        titre = str(data.get("titre", "")).strip()
        priorite = data.get("priorite", "normale")
        if not titre or priorite not in VALID_PRIORITIES:
            return jsonify(erreur="titre obligatoire, priorite parmi basse/normale/haute"), 400
        ticket = {
            "id": max((t["id"] for t in tickets), default=0) + 1,
            "titre": titre,
            "priorite": priorite,
            "statut": "ouvert",
        }
        tickets.append(ticket)
        return jsonify(ticket), 201

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(erreur="ressource introuvable"), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
