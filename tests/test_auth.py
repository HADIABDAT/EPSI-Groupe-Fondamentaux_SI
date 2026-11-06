from datetime import timedelta

import jwt
import pytest

from novaservices.models import User, utcnow

VALID = {"name": "Hugo Lambert", "email": "hugo.lambert@novaservices.fr", "password": "motdepasse", "service": "Commercial"}


def test_inscription_cree_un_utilisateur_et_renvoie_un_jeton(client):
    response = client.post("/api/auth/register", json=VALID)
    assert response.status_code == 201
    data = response.get_json()
    assert data["user"]["role"] == "user"
    assert data["user"]["email"] == "hugo.lambert@novaservices.fr"
    assert "password" not in data["user"] and "password_hash" not in data["user"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {data['token']}"})
    assert me.get_json()["name"] == "Hugo Lambert"


def test_inscription_ignore_un_role_demande(client):
    response = client.post("/api/auth/register", json=VALID | {"role": "admin"})
    assert response.get_json()["user"]["role"] == "user"


def test_inscription_normalise_l_email(client):
    response = client.post("/api/auth/register", json=VALID | {"email": "  Hugo.Lambert@NovaServices.fr "})
    assert response.get_json()["user"]["email"] == "hugo.lambert@novaservices.fr"


def test_mot_de_passe_stocke_hache(client, app):
    client.post("/api/auth/register", json=VALID)
    user = User.query.filter_by(email=VALID["email"]).one()
    assert user.password_hash != "motdepasse"
    assert user.check_password("motdepasse")


@pytest.mark.parametrize(
    "champ, valeur",
    [("name", "H"), ("email", "pas-un-email"), ("password", "court"), ("service", "x" * 81)],
)
def test_inscription_invalide(client, champ, valeur):
    response = client.post("/api/auth/register", json=VALID | {champ: valeur})
    assert response.status_code == 400
    assert champ in response.get_json()["champs"]


def test_inscription_email_deja_pris(client):
    client.post("/api/auth/register", json=VALID)
    response = client.post("/api/auth/register", json=VALID | {"email": "HUGO.lambert@novaservices.fr"})
    assert response.status_code == 400
    assert "email" in response.get_json()["champs"]


def test_inscription_sans_corps_json(client):
    assert client.post("/api/auth/register", data="n'importe quoi").status_code == 400


def test_connexion_reussie(client, user):
    response = client.post("/api/auth/login", json={"email": user.email, "password": "motdepasse"})
    assert response.status_code == 200
    assert response.get_json()["user"]["id"] == user.id


def test_connexion_mauvais_mot_de_passe(client, user):
    response = client.post("/api/auth/login", json={"email": user.email, "password": "mauvais"})
    assert response.status_code == 401


def test_connexion_email_inconnu_meme_message(client, user):
    inconnu = client.post("/api/auth/login", json={"email": "x@novaservices.fr", "password": "motdepasse"})
    mauvais = client.post("/api/auth/login", json={"email": user.email, "password": "mauvais"})
    assert inconnu.status_code == mauvais.status_code == 401
    assert inconnu.get_json() == mauvais.get_json()


def test_connexion_compte_desactive(client, make_user):
    user = make_user(active=False)
    response = client.post("/api/auth/login", json={"email": user.email, "password": "motdepasse"})
    assert response.status_code == 403


def test_route_protegee_sans_jeton(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/tickets").status_code == 401
    assert client.get("/api/stats").status_code == 401


def test_jeton_invalide(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer abc.def.ghi"})
    assert response.status_code == 401


def test_jeton_mal_forme(client):
    assert client.get("/api/auth/me", headers={"Authorization": "Token abc"}).status_code == 401


def test_jeton_signe_avec_un_autre_secret(client, user):
    token = jwt.encode({"sub": str(user.id), "exp": utcnow() + timedelta(hours=1)}, "autre-secret", algorithm="HS256")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_jeton_expire(client, app, user):
    token = jwt.encode(
        {"sub": str(user.id), "exp": utcnow() - timedelta(minutes=1)}, app.config["JWT_SECRET"], algorithm="HS256"
    )
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "expiré" in response.get_json()["erreur"]


def test_jeton_d_un_compte_desactive_ensuite(client, auth, user):
    headers = auth(user)
    user.active = False
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_le_role_est_relu_en_base(client, auth, user):
    headers = auth(user)
    assert client.get("/api/users", headers=headers).status_code == 403
    user.role = "admin"
    assert client.get("/api/users", headers=headers).status_code == 200


def test_modifier_son_profil(client, auth, user):
    response = client.patch("/api/auth/me", json={"name": "Léa F.", "service": "Paie"}, headers=auth(user))
    assert response.status_code == 200
    assert response.get_json()["name"] == "Léa F."
    assert response.get_json()["service"] == "Paie"


def test_modifier_son_profil_nom_invalide(client, auth, user):
    response = client.patch("/api/auth/me", json={"name": " "}, headers=auth(user))
    assert response.status_code == 400
    assert user.name == "Léa Fournier"


def test_le_profil_ne_change_pas_le_role(client, auth, user):
    client.patch("/api/auth/me", json={"role": "admin"}, headers=auth(user))
    assert user.role == "user"


def test_changer_son_mot_de_passe(client, auth, user):
    response = client.post("/api/auth/me/password", json={"current": "motdepasse", "new": "nouveau-secret"}, headers=auth(user))
    assert response.status_code == 200
    assert client.post("/api/auth/login", json={"email": user.email, "password": "nouveau-secret"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": user.email, "password": "motdepasse"}).status_code == 401


def test_changer_son_mot_de_passe_mauvais_actuel(client, auth, user):
    response = client.post("/api/auth/me/password", json={"current": "faux", "new": "nouveau-secret"}, headers=auth(user))
    assert response.status_code == 400
    assert "current" in response.get_json()["champs"]


def test_changer_son_mot_de_passe_trop_court(client, auth, user):
    response = client.post("/api/auth/me/password", json={"current": "motdepasse", "new": "court"}, headers=auth(user))
    assert response.status_code == 400
    assert user.check_password("motdepasse")
