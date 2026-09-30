from carpox.journal import Journal


def test_append_numerote_et_persiste(tmp_path, journal):
    a = journal.append({"type": "trip", "km": 1})
    b = journal.append({"type": "trip", "km": 2})
    assert (a["seq"], b["seq"]) == (1, 2)
    reopened = Journal(journal.path, journal.state_path)
    assert reopened.last_seq() == 2
    assert [e["km"] for e in reopened.all()] == [1, 2]


def test_synchro_et_compaction(journal):
    for i in range(10):
        journal.append({"type": "trip", "km": i})
    journal.mark_synced(7)
    assert journal.pending_count() == 3
    assert [e["seq"] for e in journal.unsynced()] == [8, 9, 10]
    removed = journal.compact(keep_synced=2)
    assert removed == 5
    assert [e["seq"] for e in journal.all()] == [6, 7, 8, 9, 10]
    journal.mark_synced(99)  # le serveur ne peut pas confirmer plus que ce qui existe
    assert journal.synced_seq == 10


def test_ligne_tronquee_ignoree(journal):
    journal.append({"type": "trip", "km": 1})
    with open(journal.path, "a") as f:
        f.write('{"type": "tr')
    assert len(journal.all()) == 1


def test_lecture_limitee_en_taille(journal):
    track = [[50.0 + i / 1000, 4.0] for i in range(200)]
    for i in range(5):
        journal.append({"type": "trip", "km": i, "track": track})
    batch = journal.unsynced(max_bytes=10000)
    assert 1 <= len(batch) < 5
    assert len(journal.unsynced(max_bytes=10)) == 1  # toujours au moins un
    recent = journal.recent(2, "trip")
    assert [e["seq"] for e in recent] == [4, 5]
    assert "track" not in recent[0]
