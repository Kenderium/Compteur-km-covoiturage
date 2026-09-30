from pathlib import Path

import pytest

from carpox_core.ledger import compute_ledger, settle
from carpox_core.legacy import parse_legacy_history

DATA = Path(__file__).parent / "data"


def trip(km, driver, *passengers):
    return {"type": "trip", "km": km, "driver": driver, "passengers": list(passengers)}


def test_plein_paye_par_le_conducteur():
    events = [
        trip(100, "Loic", "Julien"),
        {"type": "fuel", "amount_cents": 1000, "payer": "Loic"},
    ]
    ledger = compute_ledger(events)
    assert ledger["balances"] == {"Loic": 500, "Julien": -500}
    assert settle(ledger["balances"]) == [{"from": "Julien", "to": "Loic", "amount_cents": 500}]


def test_conducteurs_differents_entre_deux_pleins():
    events = [
        trip(100, "Julien", "Loic"),
        trip(100, "Loic", "Julien", "Lucas", "Eduardo"),
        {"type": "fuel", "amount_cents": 8000, "payer": "Julien"},
    ]
    ledger = compute_ledger(events)
    # Parts : Julien 20+10, Loic 20+10, Lucas 10, Eduardo 10 ; Julien a payé 80.
    assert ledger["balances"] == {"Julien": 5000, "Loic": -3000, "Lucas": -1000, "Eduardo": -1000}
    assert sum(ledger["balances"].values()) == 0


def test_trajets_apres_le_dernier_plein_en_attente():
    events = [
        trip(10, "A", "B"),
        {"type": "fuel", "amount_cents": 1000, "payer": "A"},
        trip(20, "B", "A"),
    ]
    ledger = compute_ledger(events)
    assert [t["km"] for t in ledger["pending_trips"]] == [20]


def test_remboursement_et_frais():
    events = [
        trip(10, "A", "B"),
        {"type": "fuel", "amount_cents": 1000, "payer": "A"},
        {"type": "expense", "amount_cents": 600, "payer": "B", "shared_with": ["A", "B", "C"]},
        {"type": "payment", "from": "B", "to": "A", "amount_cents": 500},
    ]
    ledger = compute_ledger(events)
    # A: +1000-500-200-500 = -200 ; B: -500+600-200+500 = +400 ; C: -200
    assert ledger["balances"] == {"A": -200, "B": 400, "C": -200}


def test_settle_minimise_les_virements():
    transfers = settle({"A": 3000, "B": -1000, "C": -1000, "D": -1000})
    assert len(transfers) == 3
    assert all(t["to"] == "A" for t in transfers)
    transfers = settle({"A": 500, "B": 500, "C": -1000})
    assert sorted((t["to"], t["amount_cents"]) for t in transfers) == [("A", 500), ("B", 500)]


def test_legacy_format_avec_crochets():
    events = parse_legacy_history((DATA / "historique_legacy_1.txt").read_text())
    assert events[0] == {"type": "trip", "km": 60.0, "driver": "Loic", "passengers": ["Eduardo"], "temp_c": 16.27709}
    assert len(events) == 4


def test_legacy_sans_crochets_garde_le_dernier_passager():
    events = parse_legacy_history((DATA / "historique_legacy_2.txt").read_text())
    last = events[-1]
    assert last["passengers"] == ["Julien", "Lucas"]  # l'ancien parseur perdait Lucas
    assert sum(1 for e in events if e["type"] == "fuel") == 2


def test_legacy_puis_plein_prix_inconnu_ne_casse_rien():
    events = parse_legacy_history((DATA / "historique_legacy_2.txt").read_text())
    ledger = compute_ledger(events)
    assert ledger["balances"] == {}
    assert len(ledger["pending_trips"]) == 1


def test_legacy_ligne_illisible():
    with pytest.raises(ValueError):
        parse_legacy_history("abc def")
