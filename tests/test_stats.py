from datetime import timedelta

from novaservices.models import db, utcnow


def test_stats_vides(client, auth, admin):
    data = client.get("/api/stats", headers=auth(admin)).get_json()
    assert data["total"] == data["open"] == data["unassigned"] == 0
    assert data["avg_resolution_hours"] is None
    assert len(data["daily"]) == 14
    assert data["daily"][-1]["date"] == utcnow().date().isoformat()
    assert data["workload"] == [{"id": admin.id, "name": "Camille Martin", "open": 0}]


def test_stats_admin(client, auth, admin, user, make_ticket):
    make_ticket(user, priority="critique")
    pris = make_ticket(user, category="reseau")
    resolu = make_ticket(user)
    client.patch(f"/api/tickets/{pris.id}", json={"assigned_to_id": admin.id}, headers=auth(admin))
    client.patch(f"/api/tickets/{resolu.id}", json={"status": "resolu"}, headers=auth(admin))

    data = client.get("/api/stats", headers=auth(admin)).get_json()
    assert (data["total"], data["open"], data["unassigned"], data["critical_open"]) == (3, 2, 1, 1)
    assert data["resolved_7d"] == 1
    assert data["by_status"]["en_cours"] == 1 and data["by_status"]["resolu"] == 1
    assert data["by_category"]["reseau"] == 1
    assert sum(data["by_priority"].values()) == data["open"]
    assert data["daily"][-1] == data["daily"][-1] | {"created": 3, "resolved": 1}
    assert data["workload"][0]["open"] == 1
    assert [t["priority"] for t in data["queue"]] == ["critique"]


def test_les_tranches_d_anciennete_couvrent_tous_les_tickets_ouverts(client, auth, admin, user, make_ticket):
    for jours in (0, 2, 5, 10):
        ticket = make_ticket(user)
        ticket.created_at = utcnow() - timedelta(days=jours, hours=1)
    db.session.commit()
    ages = client.get("/api/stats", headers=auth(admin)).get_json()["ages"]
    assert [len(a["tickets"]) for a in ages] == [1, 1, 1, 1]


def test_delai_moyen_de_resolution(client, auth, admin, user, make_ticket):
    for heures in (2, 6):
        ticket = make_ticket(user)
        ticket.created_at = utcnow() - timedelta(hours=heures)
        db.session.commit()
        client.patch(f"/api/tickets/{ticket.id}", json={"status": "resolu"}, headers=auth(admin))
    assert client.get("/api/stats", headers=auth(admin)).get_json()["avg_resolution_hours"] == 4.0


def test_stats_utilisateur_limitees_a_ses_tickets(client, auth, user, make_user, make_ticket):
    make_ticket(user)
    make_ticket(make_user())
    data = client.get("/api/stats", headers=auth(user)).get_json()
    assert data["total"] == 1
    assert "workload" not in data
    assert len(data["active"]) == 1
