import pytest

from carpox.badges import Badges
from carpox.journal import Journal


@pytest.fixture
def journal(tmp_path):
    return Journal(str(tmp_path / "journal.jsonl"), str(tmp_path / "state.json"))


@pytest.fixture
def badges(tmp_path):
    return Badges(str(tmp_path / "badges.json"))
