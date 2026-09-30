import pytest

from carpox_core.costs import distribute, person_km, split_cost


def trip(km, driver, *passengers):
    return {"km": km, "driver": driver, "passengers": list(passengers)}


def test_distribute_somme_exacte():
    shares = distribute(1000, {"a": 1, "b": 1, "c": 1})
    assert sum(shares.values()) == 1000
    assert sorted(shares.values()) == [333, 333, 334]


def test_trajet_a_quatre_partage_egal():
    shares = split_cost([trip(100, "Loic", "Julien", "Lucas", "Eduardo")], 4000)
    assert shares == {"Loic": 1000, "Julien": 1000, "Lucas": 1000, "Eduardo": 1000}


def test_trajet_seul_paye_par_le_conducteur():
    trips = [trip(100, "Loic"), trip(100, "Loic", "Julien", "Lucas", "Eduardo")]
    shares = split_cost(trips, 8000)
    # 40 € par trajet ; le trajet seul revient à Loic, l'autre est divisé en 4.
    assert shares == {"Loic": 5000, "Julien": 1000, "Lucas": 1000, "Eduardo": 1000}


def test_somme_toujours_exacte():
    trips = [trip(37.3, "A", "B"), trip(12.9, "B", "C", "D"), trip(3.3, "D")]
    for amount in (1, 7, 999, 8418, 12345):
        assert sum(split_cost(trips, amount).values()) == amount


def test_km_compteur_non_enregistres():
    # Ancien bug : avec km_tot=750 le total réparti tombait à 5,61 € sur 84,18 €.
    trips = [trip(60, "Loic", "Eduardo"), trip(30, "Loic", "Julien")]
    shares = split_cost(trips, 8418, distance_km=750, untracked_to="Loic")
    assert sum(shares.values()) == 8418
    # Les passagers ne paient que leurs trajets : 90 km sur 750.
    assert shares["Eduardo"] == pytest.approx(8418 * 30 / 750, abs=1)
    assert shares["Julien"] == pytest.approx(8418 * 15 / 750, abs=1)


def test_km_non_enregistres_demandent_un_responsable():
    with pytest.raises(ValueError):
        split_cost([trip(10, "A")], 1000, distance_km=100)


def test_aucun_trajet_tout_au_responsable():
    assert split_cost([], 5000, untracked_to="A") == {"A": 5000}


def test_passager_en_double_et_conducteur_passager():
    shares = split_cost([trip(10, "A", "B", "B", "A")], 1000)
    assert shares == {"A": 500, "B": 500}


def test_person_km():
    km = person_km([trip(60, "Loic", "Julien", "Lucas"), trip(30, "Julien")])
    assert km == {"Loic": 60, "Julien": 90, "Lucas": 60}
