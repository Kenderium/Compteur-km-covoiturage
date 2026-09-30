"""Protocole de synchronisation avec le serveur, indépendant du transport.

Le boîtier envoie ses événements non confirmés ; le serveur répond :
    {"acked_seq": int, "badges": {uid: nom}, "server_time": unix}
Le même format sert pour la synchro WiFi directe et pour le relais via l'app.
"""

BATCH_SIZE = 50
# Les parcours GPS pèsent quelques Ko : on limite aussi la taille d'un envoi
# pour tenir dans la mémoire du Pico W.
BATCH_BYTES = 12000


def build_payload(device_id, journal, limit=BATCH_SIZE):
    events = journal.unsynced(limit, BATCH_BYTES)
    return {"device_id": device_id, "events": events, "last_seq": journal.last_seq()}


def apply_response(response, journal, badges=None, clock=None):
    """Applique la réponse du serveur. Retourne le nombre d'événements confirmés."""
    before = journal.synced_seq
    acked = response.get("acked_seq")
    if isinstance(acked, int):
        journal.mark_synced(acked)
    if badges is not None and isinstance(response.get("badges"), dict):
        badges.replace_all(response["badges"])
    if clock is not None and response.get("server_time"):
        clock.set_unix_time(response["server_time"])
    return journal.synced_seq - before


def sync_all(post, device_id, journal, badges=None, clock=None, max_rounds=20):
    """Envoie tout ce qui reste par lots. `post(payload) -> dict` fait le transport.

    Retourne le nombre total d'événements confirmés. Lève l'exception du
    transport en cas d'échec (le journal reste intact, on réessaiera).
    """
    total = 0
    for _ in range(max_rounds):
        payload = build_payload(device_id, journal)
        response = post(payload)
        acked = apply_response(response, journal, badges, clock)
        total += acked
        if not payload["events"] or acked == 0 or journal.pending_count() == 0:
            break
    return total
