import pytest

from carpox.drive import DriveRecorder
from carpox.track import Track

STEP = 0.5 / 111.195  # 500 m vers le nord


def test_segment_hors_trajet():
    d = DriveRecorder()
    # Voiture garée : le GPS tremble de quelques mètres, rien n'est compté.
    for i in range(10):
        d.add_fix(50.0 + (i % 2) * 0.00005, 4.0, t_s=i, now_s=i, unix_ts=1000 + i)
    assert not d.active
    assert d.close() is None
    # Elle roule 10 km.
    for i in range(1, 21):
        d.add_fix(50.0 + i * STEP, 4.0, t_s=100 + i * 30, now_s=100 + i * 30, unix_ts=2000 + i * 30)
    assert d.active and d.km == pytest.approx(10.0, abs=0.05)
    assert d.idle_for(700) == 0
    assert d.idle_for(900) == 200
    event = d.close()
    assert event["type"] == "drive"
    assert event["km"] == pytest.approx(10.0, abs=0.05)
    assert event["start"] == 2030 and event["end"] == 2600
    # Le parcours part de la place de parking.
    assert event["track"][0] == [50.0, 4.0]
    assert event["track"][-1][0] == pytest.approx(50.0 + 20 * STEP, abs=1e-5)
    assert not d.active


def test_segment_suivant_repart_de_la_derniere_position():
    d = DriveRecorder()
    d.add_fix(50.0, 4.0, t_s=0, now_s=0)
    d.add_fix(50.0 + STEP, 4.0, t_s=60, now_s=60)
    d.close()
    d.add_fix(50.0 + 2 * STEP, 4.0, t_s=600, now_s=600)
    assert d.km == pytest.approx(0.5, abs=0.01)
    # Un trajet badgé commence : le segment suivant ne doit pas recompter ses km.
    d.close(keep_position=False)
    d.add_fix(50.0 + 30 * STEP, 4.0, t_s=900, now_s=900)
    assert not d.active


def test_coupure_du_contact():
    d = DriveRecorder()
    d.add_fix(50.0, 4.0, t_s=0, now_s=0, unix_ts=10)
    d.add_fix(50.0 + STEP, 4.0, t_s=60, now_s=60, unix_ts=70)
    saved = d.snapshot()
    d2 = DriveRecorder()
    d2.restore(saved)
    event = d2.close(keep_position=False)
    assert event["km"] == pytest.approx(0.5, abs=0.01)
    assert event["start"] == 70 and event["end"] == 70
    assert len(event["track"]) == 2


def test_parcours_reste_petit():
    t = Track(min_step_m=100, max_points=50)
    for i in range(2000):
        t.add(50.0 + i * 0.0015, 4.0)  # ~167 m entre points, ~333 km
    points = t.finish()
    assert len(points) <= 51
    assert points[0] == [50.0, 4.0]
    assert points[-1][0] == pytest.approx(50.0 + 1999 * 0.0015, abs=1e-5)
