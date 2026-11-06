import pytest

from novaservices.models import Ticket, db


def test_creer_un_ticket(client, auth, user):
    response = client.post(
        "/api/tickets",
        json={"title": "VPN refusé", "description": "Authentification échouée depuis ce matin.", "category": "acces", "priority": "haute"},
        headers=auth(user),
    )
    assert response.status_code == 201
    ticket = response.get_json()
    assert ticket["status"] == "ouvert"
    assert ticket["created_by"] == {"id": user.id, "name": "Léa Fournier"}
    assert ticket["assigned_to"] is None
    assert [e["kind"] for e in ticket["events"]] == ["created"]


@pytest.mark.parametrize(
    "champ, valeur",
    [("title", "abc"), ("title", "x" * 121), ("description", "court"), ("category", "cuisine"), ("priority", "urgente")],
)
def test_creer_un_ticket_invalide(client, auth, user, champ, valeur):
    payload = {"title": "Écran noir", "description": "L'écran reste noir au démarrage.", "category": "materiel", "priority": "normale"}
    response = client.post("/api/tickets", json=payload | {champ: valeur}, headers=auth(user))
    assert response.status_code == 400
    assert champ in response.get_json()["champs"]
    assert Ticket.query.count() == 0


def test_le_statut_ne_se_choisit_pas_a_la_creation(client, auth, user, make_ticket):
    ticket = make_ticket(user, status="resolu", assigned_to_id=1)
    assert ticket.status == "ouvert"
    assert ticket.assigned_to_id is None


def test_lister_les_tickets_pagines(client, auth, user, make_ticket):
    for _ in range(25):
        make_ticket(user)
    page1 = client.get("/api/tickets?per_page=10", headers=auth(user)).get_json()
    assert (page1["total"], page1["pages"], len(page1["items"])) == (25, 3, 10)
    page3 = client.get("/api/tickets?per_page=10&page=3", headers=auth(user)).get_json()
    assert len(page3["items"]) == 5


def test_page_hors_limites_ramenee_a_la_derniere(client, auth, user, make_ticket):
    make_ticket(user)
    data = client.get("/api/tickets?page=99&per_page=abc", headers=auth(user)).get_json()
    assert data["page"] == 1 and len(data["items"]) == 1


def test_filtres(client, auth, user, admin, make_ticket):
    make_ticket(user, priority="critique", category="reseau")
    make_ticket(user, priority="basse", title="Demande de second écran")
    pris = make_ticket(user, title="Souris sans fil introuvable")
    client.patch(f"/api/tickets/{pris.id}", json={"assigned_to_id": admin.id}, headers=auth(admin))

    def ids(query):
        return {t["id"] for t in client.get(f"/api/tickets?{query}", headers=auth(admin)).get_json()["items"]}

    assert len(ids("priority=critique")) == 1
    assert len(ids("category=reseau")) == 1
    assert ids("assigned=moi") == {pris.id}
    assert len(ids("assigned=aucun")) == 2
    assert ids("status=en_cours") == {pris.id}
    assert len(ids("status=actifs")) == 3
    assert ids("q=souris") == {pris.id}
    assert ids(f"q=%23{pris.id}") == {pris.id}
    assert len(ids("priority=inconnue")) == 3


def test_tri_par_priorite(client, auth, admin, user, make_ticket):
    make_ticket(user, priority="basse")
    make_ticket(user, priority="critique")
    make_ticket(user, priority="haute")
    items = client.get("/api/tickets?sort=priorite", headers=auth(admin)).get_json()["items"]
    assert [t["priority"] for t in items] == ["critique", "haute", "basse"]


def test_compteurs_par_statut(client, auth, user, make_ticket):
    make_ticket(user)
    make_ticket(user)
    counts = client.get("/api/tickets/counts", headers=auth(user)).get_json()
    assert counts["ouvert"] == 2 and counts["resolu"] == 0


def test_detail_d_un_ticket(client, auth, user, make_ticket):
    ticket = make_ticket(user)
    data = client.get(f"/api/tickets/{ticket.id}", headers=auth(user)).get_json()
    assert data["description"] == "L'imprimante du 2e étage n'apparaît plus."
    assert data["comments"] == []


def test_ticket_inexistant(client, auth, user):
    assert client.get("/api/tickets/999", headers=auth(user)).status_code == 404


def test_l_admin_prend_un_ticket_ouvert(client, auth, admin, user, make_ticket):
    ticket = make_ticket(user)
    data = client.patch(f"/api/tickets/{ticket.id}", json={"assigned_to_id": admin.id}, headers=auth(admin)).get_json()
    assert data["assigned_to"]["id"] == admin.id
    assert data["status"] == "en_cours"
    assert [e["kind"] for e in data["events"]] == ["created", "assigned", "status"]


def test_desassigner(client, auth, admin, user, make_ticket):
    ticket = make_ticket(user)
    client.patch(f"/api/tickets/{ticket.id}", json={"assigned_to_id": admin.id}, headers=auth(admin))
    data = client.patch(f"/api/tickets/{ticket.id}", json={"assigned_to_id": None}, headers=auth(admin)).get_json()
    assert data["assigned_to"] is None
    assert data["events"][-1] == data["events"][-1] | {"kind": "assigned", "old": "Camille Martin", "new": None}


def test_on_n_assigne_pas_a_un_simple_utilisateur(client, auth, admin, user, make_ticket):
    ticket = make_ticket(user)
    response = client.patch(f"/api/tickets/{ticket.id}", json={"assigned_to_id": user.id}, headers=auth(admin))
    assert response.status_code == 400
    assert "assigned_to_id" in response.get_json()["champs"]


def test_on_n_assigne_pas_a_un_admin_desactive(client, auth, admin, make_user, user, make_ticket):
    absent = make_user(role="admin", active=False)
    ticket = make_ticket(user)
    response = client.patch(f"/api/tickets/{ticket.id}", json={"assigned_to_id": absent.id}, headers=auth(admin))
    assert response.status_code == 400


def test_resoudre_puis_rouvrir(client, auth, admin, user, make_ticket):
    ticket = make_ticket(user)
    client.patch(f"/api/tickets/{ticket.id}", json={"status": "resolu"}, headers=auth(admin))
    assert ticket.resolved_at is not None
    client.patch(f"/api/tickets/{ticket.id}", json={"status": "ouvert"}, headers=auth(user))
    assert ticket.status == "ouvert" and ticket.resolved_at is None


def test_changer_priorite_et_categorie_trace_l_historique(client, auth, admin, user, make_ticket):
    ticket = make_ticket(user)
    data = client.patch(
        f"/api/tickets/{ticket.id}", json={"priority": "critique", "category": "reseau"}, headers=auth(admin)
    ).get_json()
    events = {e["kind"]: (e["old"], e["new"]) for e in data["events"]}
    assert events["priority"] == ("normale", "critique")
    assert events["category"] == ("materiel", "reseau")


def test_un_changement_sans_effet_ne_trace_rien(client, auth, admin, user, make_ticket):
    ticket = make_ticket(user)
    data = client.patch(f"/api/tickets/{ticket.id}", json={"priority": "normale", "status": "ouvert"}, headers=auth(admin)).get_json()
    assert len(data["events"]) == 1


@pytest.mark.parametrize("payload", [{"status": "perdu"}, {"priority": "max"}, {"category": "cuisine"}])
def test_mise_a_jour_invalide(client, auth, admin, user, make_ticket, payload):
    ticket = make_ticket(user)
    assert client.patch(f"/api/tickets/{ticket.id}", json=payload, headers=auth(admin)).status_code == 400


def test_supprimer_un_ticket(client, auth, admin, user, make_ticket):
    ticket = make_ticket(user)
    ticket_id = ticket.id
    assert client.delete(f"/api/tickets/{ticket_id}", headers=auth(admin)).status_code == 204
    assert db.session.get(Ticket, ticket_id) is None
    assert client.delete(f"/api/tickets/{ticket_id}", headers=auth(admin)).status_code == 404


def test_commenter(client, auth, admin, user, make_ticket):
    ticket = make_ticket(user)
    response = client.post(f"/api/tickets/{ticket.id}/comments", json={"body": "Je regarde."}, headers=auth(admin))
    assert response.status_code == 201
    comment = response.get_json()["comments"][0]
    assert comment["body"] == "Je regarde." and comment["author_role"] == "admin"


def test_commentaire_vide(client, auth, user, make_ticket):
    ticket = make_ticket(user)
    assert client.post(f"/api/tickets/{ticket.id}/comments", json={"body": "   "}, headers=auth(user)).status_code == 400


def test_la_reponse_du_demandeur_relance_le_ticket(client, auth, admin, user, make_ticket):
    ticket = make_ticket(user)
    client.patch(f"/api/tickets/{ticket.id}", json={"status": "en_attente"}, headers=auth(admin))
    data = client.post(f"/api/tickets/{ticket.id}/comments", json={"body": "Oui, sur deux postes."}, headers=auth(user)).get_json()
    assert data["status"] == "en_cours"


def test_la_reponse_du_support_ne_change_pas_le_statut(client, auth, admin, user, make_ticket):
    ticket = make_ticket(user)
    client.patch(f"/api/tickets/{ticket.id}", json={"status": "en_attente"}, headers=auth(admin))
    data = client.post(f"/api/tickets/{ticket.id}/comments", json={"body": "Une relance."}, headers=auth(admin)).get_json()
    assert data["status"] == "en_attente"


def test_pas_de_commentaire_sur_un_ticket_ferme(client, auth, user, make_ticket):
    ticket = make_ticket(user)
    client.patch(f"/api/tickets/{ticket.id}", json={"status": "ferme"}, headers=auth(user))
    response = client.post(f"/api/tickets/{ticket.id}/comments", json={"body": "Encore là ?"}, headers=auth(user))
    assert response.status_code == 409
