import math

import pytest

from carpox_core.geo import DistanceAccumulator, haversine_km, to_decimal


def test_haversine_bruxelles_paris():
    # Grand-Place de Bruxelles -> Notre-Dame de Paris : ~264 km à vol d'oiseau.
    d = haversine_km(50.8467, 4.3525, 48.8530, 2.3499)
    assert d == pytest.approx(264.0, abs=2.0)


def test_haversine_symetrique_et_nul():
    assert haversine_km(50.0, 4.0, 50.0, 4.0) == 0.0
    a = haversine_km(50.6, 4.6, 50.7, 4.4)
    b = haversine_km(50.7, 4.4, 50.6, 4.6)
    assert a == pytest.approx(b)


def test_un_degre_de_latitude():
    assert haversine_km(0, 0, 1, 0) == pytest.approx(111.19, abs=0.05)


def test_longitude_utilisee_correctement():
    # L'ancienne formule lisait la latitude à la place de la longitude.
    assert haversine_km(50.0, 4.0, 50.0, 5.0) == pytest.approx(71.5, abs=0.5)


def test_to_decimal():
    assert to_decimal(50, 30.0, "N") == pytest.approx(50.5)
    assert to_decimal(4, 15.0, "W") == pytest.approx(-4.25)


def test_accumulateur_ignore_le_tremblement():
    acc = DistanceAccumulator(min_step_m=25)
    lat, lon = 50.6680, 4.6118
    acc.add(lat, lon, t_s=0)
    # 10 m de bruit autour du point de départ, 60 fois.
    for i in range(60):
        dlat = (10 / 111_000) * (1 if i % 2 else -1)
        acc.add(lat + dlat, lon, t_s=i + 1)
    assert acc.total_km == 0.0


def test_accumulateur_trajet_droit():
    acc = DistanceAccumulator()
    # 10 km vers le nord, un point toutes les 10 s à ~72 km/h.
    step = 0.2 / 111.195  # 200 m en degrés de latitude
    for i in range(51):
        acc.add(50.0 + i * step, 4.0, t_s=i * 10)
    assert acc.total_km == pytest.approx(10.0, abs=0.05)


def test_accumulateur_rejette_saut_impossible_et_hdop():
    acc = DistanceAccumulator()
    acc.add(50.0, 4.0, t_s=0)
    assert not acc.add(51.0, 4.0, t_s=1)  # 111 km en 1 s
    assert not acc.add(50.01, 4.0, t_s=60, hdop=12.0)
    assert not acc.add(0.0, 0.0, t_s=61)  # pas de fix
    assert acc.add(50.01, 4.0, t_s=60)
    assert acc.total_km == pytest.approx(1.112, abs=0.01)
