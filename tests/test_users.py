def test_lister_les_comptes_avec_leurs_compteurs(client, auth, admin, user, make_ticket):
    ticket = make_ticket(user)
    client.patch(f"/api/tickets/{ticket.id}", json={"assigned_to_id": admin.id}, headers=auth(admin))
    users = {u["name"]: u for u in client.get("/api/users", headers=auth(admin)).get_json()}
    assert users["Léa Fournier"]["open_requests"] == 1
    assert users["Camille Martin"]["open_assigned"] == 1


def test_filtrer_les_comptes(client, auth, admin, user):
    admins = client.get("/api/users?role=admin", headers=auth(admin)).get_json()
    assert [u["name"] for u in admins] == ["Camille Martin"]
    found = client.get("/api/users?q=fournier", headers=auth(admin)).get_json()
    assert [u["name"] for u in found] == ["Léa Fournier"]


def test_creer_un_compte_admin(client, auth, admin):
    payload = {"name": "Yanis Benali", "email": "yanis.benali@novaservices.fr", "password": "motdepasse", "role": "admin"}
    response = client.post("/api/users", json=payload, headers=auth(admin))
    assert response.status_code == 201
    assert response.get_json()["role"] == "admin"
    login = client.post("/api/auth/login", json={"email": payload["email"], "password": "motdepasse"})
    assert login.status_code == 200


def test_creer_un_compte_role_inconnu(client, auth, admin):
    payload = {"name": "Yanis Benali", "email": "yanis@novaservices.fr", "password": "motdepasse", "role": "chef"}
    response = client.post("/api/users", json=payload, headers=auth(admin))
    assert response.status_code == 400
    assert "role" in response.get_json()["champs"]


def test_promouvoir_un_utilisateur(client, auth, admin, user):
    response = client.patch(f"/api/users/{user.id}", json={"role": "admin"}, headers=auth(admin))
    assert response.get_json()["role"] == "admin"


def test_retrograder_un_admin_libere_ses_tickets(client, auth, admin, make_user, user, make_ticket):
    collegue = make_user(role="admin")
    ticket = make_ticket(user)
    client.patch(f"/api/tickets/{ticket.id}", json={"assigned_to_id": collegue.id}, headers=auth(admin))
    client.patch(f"/api/users/{collegue.id}", json={"role": "user"}, headers=auth(admin))
    assert ticket.assigned_to_id is None


def test_desactiver_un_compte(client, auth, admin, user):
    client.patch(f"/api/users/{user.id}", json={"active": False}, headers=auth(admin))
    login = client.post("/api/auth/login", json={"email": user.email, "password": "motdepasse"})
    assert login.status_code == 403


def test_un_admin_ne_se_retire_pas_ses_droits(client, auth, admin):
    assert client.patch(f"/api/users/{admin.id}", json={"role": "user"}, headers=auth(admin)).status_code == 400
    assert client.patch(f"/api/users/{admin.id}", json={"active": False}, headers=auth(admin)).status_code == 400
    assert admin.role == "admin" and admin.active


def test_modifier_un_compte_inexistant(client, auth, admin):
    assert client.patch("/api/users/999", json={"role": "admin"}, headers=auth(admin)).status_code == 404
