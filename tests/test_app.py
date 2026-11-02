import pytest

from app import create_app


@pytest.fixture
def client():
    return create_app().test_client()


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


def test_liste_des_tickets(client):
    response = client.get("/tickets")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 3
    assert {"id", "titre", "priorite", "statut"} <= data[0].keys()


def test_filtre_par_statut(client):
    data = client.get("/tickets?statut=ouvert").get_json()
    assert [t["id"] for t in data] == [1]


def test_ticket_par_id(client):
    response = client.get("/tickets/2")
    assert response.status_code == 200
    assert response.get_json()["titre"] == "Accès VPN refusé"


def test_creation_de_ticket(client):
    response = client.post("/tickets", json={"titre": "Souris cassée", "priorite": "basse"})
    assert response.status_code == 201
    ticket = response.get_json()
    assert ticket == {"id": 4, "titre": "Souris cassée", "priorite": "basse", "statut": "ouvert"}
    assert client.get("/tickets/4").status_code == 200


@pytest.mark.parametrize("payload", [{}, {"titre": "  "}, {"titre": "X", "priorite": "urgente"}])
def test_creation_invalide_renvoie_400(client, payload):
    assert client.post("/tickets", json=payload).status_code == 400


def test_ticket_inexistant_renvoie_404(client):
    assert client.get("/tickets/999").status_code == 404


def test_route_inexistante_renvoie_404(client):
    assert client.get("/route-inconnue").status_code == 404
