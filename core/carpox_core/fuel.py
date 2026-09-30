"""Estimation du carburant restant dans le réservoir.

On part de la même suite ordonnée d'événements que le calcul des soldes
(voir carpox_core.ledger). Les km comptés depuis le dernier plein sont ceux
des trajets badgés et des km roulés sans badge ("drive").

Hypothèse : chaque plein remplit le réservoir. Alors, juste après un plein,
le réservoir est plein, et le carburant restant vaut
    réservoir - km depuis le plein × consommation / 100.

La consommation est mesurée quand les pleins indiquent les litres mis : les
litres d'un plein ont servi à rouler les km depuis le plein précédent. À
défaut, on prend la consommation moyenne réglée par le propriétaire.
"""

# Au-delà, une mesure est sûrement fausse (plein partiel, km oubliés...).
MIN_L_100KM = 2.0
MAX_L_100KM = 30.0


def measured_consumption(samples, max_samples=5):
    """Consommation moyenne (L/100 km) des derniers pleins, ou None.

    `samples` est une liste de (litres, km). On pondère par les km : c'est
    le total des litres divisé par le total des km.
    """
    litres = 0.0
    km = 0.0
    for sample in samples[-max_samples:]:
        litres += sample[0]
        km += sample[1]
    if km <= 0:
        return None
    value = 100.0 * litres / km
    if value < MIN_L_100KM or value > MAX_L_100KM:
        return None
    return value


def fuel_status(events, tank_l=None, consumption_l_100km=None):
    """Retourne un dict décrivant l'état estimé du réservoir.

    Clés : km_since_fill, fills, last_fill (événement du dernier plein ou
    None), measured_l_100km, consumption_l_100km, consumption_source
    ("measured", "configured" ou None), remaining_l, remaining_pct, range_km.
    Les trois dernières valent None quand on ne peut pas estimer.
    """
    km_since = 0.0
    samples = []
    last_fill = None
    fills = 0
    for event in events:
        kind = event.get("type")
        if kind in ("trip", "drive"):
            km_since += event.get("km", 0) or 0
        elif kind == "fuel":
            period = km_since
            distance = event.get("distance_km")
            if distance is not None and distance > period:
                period = distance
            litres = event.get("litres")
            # Le tout premier plein ne dit rien : on ignore l'état du réservoir avant.
            if last_fill is not None and litres and period > 0:
                samples.append((litres, period))
            last_fill = event
            fills += 1
            km_since = 0.0

    measured = measured_consumption(samples)
    if measured is not None:
        consumption, source = measured, "measured"
    elif consumption_l_100km:
        consumption, source = consumption_l_100km, "configured"
    else:
        consumption, source = None, None

    remaining = pct = range_km = None
    if tank_l and consumption and last_fill is not None:
        remaining = tank_l - km_since * consumption / 100.0
        if remaining < 0:
            remaining = 0.0
        if remaining > tank_l:
            remaining = tank_l
        pct = 100.0 * remaining / tank_l
        range_km = 100.0 * remaining / consumption

    return {
        "km_since_fill": km_since,
        "fills": fills,
        "last_fill": last_fill,
        "measured_l_100km": measured,
        "consumption_l_100km": consumption,
        "consumption_source": source,
        "remaining_l": remaining,
        "remaining_pct": pct,
        "range_km": range_km,
    }
