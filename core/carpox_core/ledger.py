"""Comptes entre covoitureurs : qui a payé quoi, et qui doit combien à qui.

On part d'une suite ordonnée d'événements (dicts avec une clé "type") :

- "trip"    : {"km", "driver", "passengers"}
- "drive"   : {"km"}  km roulés par la voiture sans trajet badgé (le boîtier
              compte les km dès qu'il est allumé). Ils sont à la charge de
              celui qui paie le plein suivant, comme les km non enregistrés.
- "fuel"    : {"amount_cents", "payer", "distance_km" (optionnel)}
              Le plein paie les trajets enregistrés depuis le plein précédent.
              "amount_cents" à None (historique ancien sans prix) clôt la
              période sans rien imputer.
- "expense" : {"amount_cents", "payer", "shared_with": [ids]}
              Frais partagés à parts égales (péage, parking...).
- "payment" : {"from", "to", "amount_cents"}  remboursement effectué.

Un solde positif signifie qu'on doit de l'argent à la personne ; négatif,
qu'elle doit de l'argent aux autres. La somme des soldes vaut toujours 0.
"""

from carpox_core.costs import distribute, split_cost, trips_km


def _add(balances, person, cents):
    balances[person] = balances.get(person, 0) + cents


def compute_ledger(events):
    """Retourne {"balances", "pending_trips", "pending_drive_km", "fuel_splits"}.

    `pending_trips` sont les trajets pas encore couverts par un plein, et
    `pending_drive_km` les km roulés sans badge depuis le dernier plein.
    `fuel_splits` détaille, pour chaque plein, la part de chacun.
    """
    balances = {}
    pending = []
    drive_km = 0.0
    fuel_splits = []
    for event in events:
        kind = event.get("type")
        if kind == "trip":
            if event.get("km", 0) > 0:
                pending.append(event)
        elif kind == "drive":
            drive_km += event.get("km", 0)
        elif kind == "fuel":
            amount = event.get("amount_cents")
            if amount is not None and amount > 0:
                payer = event["payer"]
                distance = event.get("distance_km")
                if drive_km > 0:
                    measured = trips_km(pending) + drive_km
                    if distance is None or distance < measured:
                        distance = measured
                shares = split_cost(pending, amount, distance, untracked_to=payer)
                _add(balances, payer, amount)
                for person in shares:
                    _add(balances, person, -shares[person])
                fuel_splits.append({"event": event, "shares": shares})
            pending = []
            drive_km = 0.0
        elif kind == "expense":
            amount = event["amount_cents"]
            people = event.get("shared_with") or []
            if amount > 0 and people:
                weights = {}
                for p in people:
                    weights[p] = 1
                shares = distribute(amount, weights)
                _add(balances, event["payer"], amount)
                for person in shares:
                    _add(balances, person, -shares[person])
        elif kind == "payment":
            _add(balances, event["from"], event["amount_cents"])
            _add(balances, event["to"], -event["amount_cents"])
    for person in list(balances):
        if balances[person] == 0:
            del balances[person]
    return {"balances": balances, "pending_trips": pending, "pending_drive_km": drive_km,
            "fuel_splits": fuel_splits}


def settle(balances):
    """Propose des remboursements pour remettre tous les soldes à zéro.

    Algorithme glouton : le plus gros débiteur rembourse le plus gros
    créancier. Donne au plus n-1 virements pour n personnes.

    Returns:
        liste de {"from": débiteur, "to": créancier, "amount_cents": int}
    """
    debtors = []
    creditors = []
    for person in balances:
        cents = balances[person]
        if cents < 0:
            debtors.append([-cents, person])
        elif cents > 0:
            creditors.append([cents, person])
    transfers = []
    while debtors and creditors:
        debtors.sort(key=lambda d: (-d[0], str(d[1])))
        creditors.sort(key=lambda c: (-c[0], str(c[1])))
        debt = debtors[0]
        credit = creditors[0]
        amount = min(debt[0], credit[0])
        transfers.append({"from": debt[1], "to": credit[1], "amount_cents": amount})
        debt[0] -= amount
        credit[0] -= amount
        if debt[0] == 0:
            debtors.pop(0)
        if credit[0] == 0:
            creditors.pop(0)
    return transfers
