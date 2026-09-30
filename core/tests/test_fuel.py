import pytest

from carpox_core.fuel import fuel_status


def fuel(litres=None, distance_km=None):
    e = {"type": "fuel", "amount_cents": 5000, "payer": "A"}
    if litres is not None:
        e["litres"] = litres
    if distance_km is not None:
        e["distance_km"] = distance_km
    return e


def trip(km):
    return {"type": "trip", "km": km, "driver": "A", "passengers": []}


def test_pas_d_estimation_avant_le_premier_plein():
    s = fuel_status([trip(100)], tank_l=50, consumption_l_100km=6)
    assert s["remaining_l"] is None
    assert s["km_since_fill"] == 100


def test_estimation_avec_la_consommation_reglee():
    s = fuel_status([fuel(), trip(200), {"type": "drive", "km": 50}], tank_l=50, consumption_l_100km=6)
    assert s["consumption_source"] == "configured"
    assert s["km_since_fill"] == 250
    assert s["remaining_l"] == pytest.approx(35.0)
    assert s["remaining_pct"] == pytest.approx(70.0)
    assert s["range_km"] == pytest.approx(583.33, abs=0.01)


def test_consommation_mesuree_avec_les_litres():
    events = [fuel(40), trip(500), fuel(30), trip(300), {"type": "drive", "km": 200}, fuel(35), trip(100)]
    s = fuel_status(events, tank_l=45, consumption_l_100km=8)
    # Le premier plein ne compte pas : (30 + 35) L pour (500 + 500) km.
    assert s["measured_l_100km"] == pytest.approx(6.5)
    assert s["consumption_source"] == "measured"
    assert s["remaining_l"] == pytest.approx(45 - 6.5)
    assert s["fills"] == 3
    assert s["last_fill"]["litres"] == 35


def test_mesure_absurde_ignoree():
    s = fuel_status([fuel(40), trip(10), fuel(40)], tank_l=45, consumption_l_100km=7)
    assert s["measured_l_100km"] is None
    assert s["consumption_source"] == "configured"


def test_reservoir_jamais_negatif():
    s = fuel_status([fuel(), trip(2000)], tank_l=50, consumption_l_100km=6)
    assert s["remaining_l"] == 0
    assert s["range_km"] == 0
