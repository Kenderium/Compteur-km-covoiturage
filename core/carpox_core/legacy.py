"""Import de l'ancien historique texte du boîtier (historique_trajets.txt).

Deux variantes existent dans les anciens fichiers :

    60 Loic ['Eduardo'] 16.27709     (km, conducteur, [passagers], température)
    60 Julien Alex Lucas             (km, conducteur, passagers)
    Plein                            (plein fait, prix inconnu)

L'ancien parseur coupait sur "]" et perdait le dernier passager quand il n'y
avait pas de crochets. Ici on découpe proprement en mots.
"""


def _is_number(token):
    try:
        float(token)
        return True
    except ValueError:
        return False


def parse_legacy_history(text):
    """Convertit l'ancien format en liste d'événements (voir carpox_core.ledger)."""
    events = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.lower() == "plein":
            events.append({"type": "fuel", "amount_cents": None, "payer": None})
            continue
        for ch in "[],'\"":
            line = line.replace(ch, " ")
        tokens = line.split()
        if len(tokens) < 2 or not _is_number(tokens[0]):
            raise ValueError("ligne d'historique illisible : %r" % raw)
        km = float(tokens[0])
        rest = tokens[1:]
        # Un nombre en fin de ligne est la température, pas un passager.
        temp = None
        if len(rest) > 1 and _is_number(rest[-1]):
            temp = float(rest[-1])
            rest = rest[:-1]
        if rest[0] in ("None", "none"):
            raise ValueError("trajet sans conducteur : %r" % raw)
        trip = {"type": "trip", "km": km, "driver": rest[0], "passengers": rest[1:]}
        if temp is not None:
            trip["temp_c"] = temp
        events.append(trip)
    return events
