"""Répartition des frais entre covoitureurs.

Les montants sont en centimes (entiers) pour ne jamais perdre ni créer un
centime : la somme des parts vaut toujours exactement le montant réparti.

Principe : le coût d'un plein couvre les km roulés par la voiture depuis le
plein précédent. Chaque trajet coûte `km du trajet × prix au km`, et ce coût
est partagé à parts égales entre les occupants du trajet (conducteur compris).
Un trajet fait seul est donc payé entièrement par le conducteur, et un trajet
à quatre coûte un quart à chacun.

Un trajet est un dict : {"km": float, "driver": id, "passengers": [id, ...]}.
Les identifiants de personnes sont des chaînes quelconques.
"""


def occupants(trip):
    """Liste sans doublon des personnes présentes (conducteur en premier)."""
    people = [trip["driver"]]
    for p in trip.get("passengers") or []:
        if p not in people:
            people.append(p)
    return people


def distribute(amount_cents, weights):
    """Répartit `amount_cents` au prorata de `weights` (dict id -> poids >= 0).

    Méthode du plus fort reste : chaque part est arrondie vers le bas puis les
    centimes restants vont aux plus grands restes. La somme est exacte.
    """
    total = 0.0
    for w in weights.values():
        total += w
    if total <= 0:
        raise ValueError("aucun poids positif pour répartir le montant")
    shares = {}
    remainders = []
    allocated = 0
    for key in weights:
        exact = amount_cents * weights[key] / total
        base = int(exact)
        shares[key] = base
        allocated += base
        remainders.append((exact - base, key))
    remainders.sort(key=lambda r: (-r[0], str(r[1])))
    for i in range(amount_cents - allocated):
        shares[remainders[i % len(remainders)][1]] += 1
    return shares


def trips_km(trips):
    total = 0.0
    for t in trips:
        total += t["km"]
    return total


def split_cost(trips, amount_cents, distance_km=None, untracked_to=None):
    """Répartit le coût d'un plein entre les occupants des trajets.

    Args:
        trips: trajets roulés avec ce plein.
        amount_cents: prix du plein en centimes.
        distance_km: km réellement roulés par la voiture avec ce plein (compteur
            journalier). S'il dépasse la somme des trajets enregistrés, la part
            des km non enregistrés est attribuée à `untracked_to`.
        untracked_to: personne qui paie les km non enregistrés (en général le
            propriétaire ou celui qui a payé le plein).

    Returns:
        dict id -> centimes, dont la somme vaut exactement amount_cents.
    """
    if amount_cents < 0:
        raise ValueError("montant négatif")
    tracked = trips_km(trips)
    total_km = tracked
    if distance_km is not None and distance_km > tracked:
        total_km = distance_km
    if total_km <= 0:
        if untracked_to is None:
            raise ValueError("aucun km à répartir")
        return {untracked_to: amount_cents}

    weights = {}
    for trip in trips:
        people = occupants(trip)
        per_person = trip["km"] / len(people)
        for p in people:
            weights[p] = weights.get(p, 0.0) + per_person
    untracked = total_km - tracked
    if untracked > 1e-9:
        if untracked_to is None:
            raise ValueError("des km non enregistrés demandent `untracked_to`")
        weights[untracked_to] = weights.get(untracked_to, 0.0) + untracked
    return distribute(amount_cents, weights)


def person_km(trips):
    """Km parcourus par personne (conducteur compris)."""
    km = {}
    for trip in trips:
        for p in occupants(trip):
            km[p] = km.get(p, 0.0) + trip["km"]
    return km
