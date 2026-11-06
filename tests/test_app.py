"""Routes de contrôle, pages, démarrage et données de démonstration."""

import pytest

from novaservices import create_app
from novaservices.models import Ticket, User


def test_health_repond_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_health_simule_une_panne(client, monkeypatch):
    monkeypatch.setenv("FAIL_HEALTH", "1")
    assert client.get("/health").status_code == 503


def test_version_lit_les_variables_d_environnement(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    monkeypatch.setenv("GIT_COMMIT", "abc123")
    assert client.get("/version").get_json() == {"version": "1.2.3", "commit": "abc123"}


@pytest.mark.parametrize(
    "url", ["/", "/connexion", "/inscription", "/tickets", "/tickets/nouveau", "/tickets/3", "/utilisateurs", "/compte"]
)
def test_les_pages_s_affichent(client, url):
    response = client.get(url)
    assert response.status_code == 200
    assert "text/html" in response.content_type
    assert b"NovaServices" in response.data


def test_route_inexistante_renvoie_404(client):
    assert client.get("/route-inconnue").status_code == 404


def test_route_api_inexistante_renvoie_du_json(client):
    response = client.get("/api/inconnue")
    assert response.status_code == 404
    assert response.get_json() == {"erreur": "Ressource introuvable."}


def test_methode_non_autorisee(client):
    assert client.put("/api/tickets").status_code == 405


def test_compte_admin_cree_au_demarrage(monkeypatch):
    app = create_app(
        {"SQLALCHEMY_DATABASE_URI": "sqlite://", "ADMIN_EMAIL": "Admin@NovaServices.fr", "ADMIN_PASSWORD": "motdepasse"}
    )
    with app.app_context():
        admin = User.query.filter_by(email="admin@novaservices.fr").one()
        assert admin.role == "admin" and admin.check_password("motdepasse")


def test_donnees_de_demo_coherentes():
    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://", "SEED_DEMO": True})
    with app.app_context():
        tickets = Ticket.query.all()
        assert len(tickets) == 34
        for ticket in tickets:
            assert ticket.events[0].kind == "created"
            assert (ticket.resolved_at is not None) == (ticket.status in ("resolu", "ferme"))
            assert ticket.updated_at >= ticket.created_at
            if ticket.status != "ouvert":
                assert ticket.assigned_to.is_admin
        assert User.query.filter_by(role="admin").count() == 2
