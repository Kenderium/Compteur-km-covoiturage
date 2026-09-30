import pytest
from fastapi.testclient import TestClient

from carpox_server.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.sqlite3"), app_dir=str(tmp_path / "no-app"), invite_code="")
    return TestClient(app)


def register(client, username, name=None, password="correct-horse-battery"):
    r = client.post("/api/auth/register",
                    json={"username": username, "password": password, "display_name": name or username.title()})
    assert r.status_code == 201, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


@pytest.fixture
def loic(client):
    return register(client, "loic", "Loïc")


@pytest.fixture
def julien(client):
    return register(client, "julien", "Julien")
