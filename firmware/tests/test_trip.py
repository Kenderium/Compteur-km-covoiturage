import pytest

from carpox.trip import TripRecorder


def test_trajet_complet():
    r = TripRecorder()
    r.set_driver(54835169)
    assert r.add_passenger(707308629)
    assert not r.add_passenger(707308629)
    assert not r.add_passenger(54835169)
    r.start(unix_ts=1000)
    step = 0.5 / 111.195
    for i in range(21):
        r.add_fix(50.0 + i * step, 4.0, t_s=i * 30)
    event = r.stop(unix_ts=1600, temp_c=21.456)
    assert event["driver"] == "54835169"
    assert event["passengers"] == ["707308629"]
    assert event["km"] == pytest.approx(10.0, abs=0.05)
    assert event["temp_c"] == 21.5
    assert not r.active and r.driver is None  # remis à zéro (ancien bug #6)


def test_pas_de_depart_sans_conducteur():
    with pytest.raises(ValueError):
        TripRecorder().start()


def test_points_ignores_hors_trajet():
    r = TripRecorder()
    assert not r.add_fix(50.0, 4.0)


def test_reprise_apres_coupure_de_courant():
    r = TripRecorder()
    r.set_driver("1")
    r.add_passenger("2")
    r.start(unix_ts=10)
    r.add_fix(50.0, 4.0, t_s=0)
    r.add_fix(50.01, 4.0, t_s=60)
    saved = r.snapshot()

    r2 = TripRecorder()
    r2.restore(saved)
    # Le premier point après reprise sert de nouveau départ.
    r2.add_fix(50.05, 4.0, t_s=0)
    r2.add_fix(50.06, 4.0, t_s=60)
    event = r2.stop()
    assert event["km"] == pytest.approx(2.224, abs=0.01)
    assert event["passengers"] == ["2"] and event["start"] == 10
