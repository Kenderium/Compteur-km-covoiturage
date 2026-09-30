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
