import pytest

from novaservices import create_app
from novaservices.auth import create_token
from novaservices.models import Ticket, User, db


@pytest.fixture
def app():
    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://", "JWT_SECRET": "secret-de-test", "SEED_DEMO": False})
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user(app):
    counter = {"n": 0}

    def make(role="user", name=None, active=True, password="motdepasse"):
        counter["n"] += 1
        user = User(
            email=f"personne{counter['n']}@novaservices.fr",
            name=name or f"Personne {counter['n']}",
            service="Comptabilité",
            role=role,
            active=active,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    return make


@pytest.fixture
def auth(app):
    def headers(user):
        return {"Authorization": f"Bearer {create_token(user)}"}

    return headers


@pytest.fixture
def user(make_user):
    return make_user(name="Léa Fournier")


@pytest.fixture
def admin(make_user):
    return make_user(role="admin", name="Camille Martin")


@pytest.fixture
def make_ticket(client, auth):
    def make(owner, **fields):
        payload = {
            "title": "Imprimante hors ligne",
            "description": "L'imprimante du 2e étage n'apparaît plus.",
            "category": "materiel",
            "priority": "normale",
        } | fields
        response = client.post("/api/tickets", json=payload, headers=auth(owner))
        assert response.status_code == 201, response.get_json()
        return db.session.get(Ticket, response.get_json()["id"])

    return make
