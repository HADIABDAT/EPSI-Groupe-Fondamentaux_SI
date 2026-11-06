"""Ce qu'un utilisateur peut faire, et surtout ce qu'il ne peut pas faire."""

import pytest


def test_un_utilisateur_ne_voit_que_ses_tickets(client, auth, user, make_user, make_ticket):
    autre = make_user()
    mien = make_ticket(user)
    make_ticket(autre)
    items = client.get("/api/tickets", headers=auth(user)).get_json()["items"]
    assert [t["id"] for t in items] == [mien.id]


def test_l_admin_voit_tous_les_tickets(client, auth, admin, user, make_user, make_ticket):
    make_ticket(user)
    make_ticket(make_user())
    assert client.get("/api/tickets", headers=auth(admin)).get_json()["total"] == 2


def test_le_ticket_d_un_autre_renvoie_404(client, auth, user, make_user, make_ticket):
    ticket = make_ticket(make_user())
    headers = auth(user)
    assert client.get(f"/api/tickets/{ticket.id}", headers=headers).status_code == 404
    assert client.patch(f"/api/tickets/{ticket.id}", json={"status": "ferme"}, headers=headers).status_code == 404
    assert client.post(f"/api/tickets/{ticket.id}/comments", json={"body": "Coucou"}, headers=headers).status_code == 404


def test_les_compteurs_d_un_utilisateur_ne_comptent_que_ses_tickets(client, auth, user, make_user, make_ticket):
    make_ticket(user)
    make_ticket(make_user())
    assert client.get("/api/tickets/counts", headers=auth(user)).get_json()["ouvert"] == 1


@pytest.mark.parametrize(
    "payload",
    [{"priority": "critique"}, {"assigned_to_id": 1}, {"category": "reseau"}, {"status": "resolu"}, {"status": "en_cours"}],
)
def test_un_utilisateur_ne_modifie_pas_le_traitement(client, auth, user, make_ticket, payload):
    ticket = make_ticket(user)
    assert client.patch(f"/api/tickets/{ticket.id}", json=payload, headers=auth(user)).status_code == 403
    assert ticket.status == "ouvert" and ticket.priority == "normale"


def test_un_utilisateur_ferme_sa_demande(client, auth, user, make_ticket):
    ticket = make_ticket(user)
    response = client.patch(f"/api/tickets/{ticket.id}", json={"status": "ferme"}, headers=auth(user))
    assert response.status_code == 200
    assert ticket.status == "ferme"


def test_un_utilisateur_ne_rouvre_pas_un_ticket_non_resolu(client, auth, user, make_ticket):
    ticket = make_ticket(user)
    client.patch(f"/api/tickets/{ticket.id}", json={"status": "ferme"}, headers=auth(user))
    assert client.patch(f"/api/tickets/{ticket.id}", json={"status": "ouvert"}, headers=auth(user)).status_code == 403


def test_un_utilisateur_ne_supprime_pas(client, auth, user, make_ticket):
    ticket = make_ticket(user)
    assert client.delete(f"/api/tickets/{ticket.id}", headers=auth(user)).status_code == 403


@pytest.mark.parametrize(
    "method, url",
    [("get", "/api/users"), ("post", "/api/users"), ("patch", "/api/users/1")],
)
def test_la_gestion_des_comptes_est_reservee_aux_admins(client, auth, user, method, url):
    response = getattr(client, method)(url, json={}, headers=auth(user))
    assert response.status_code == 403
