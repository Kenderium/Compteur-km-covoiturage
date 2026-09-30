# The Carpool Project (CarpoX)

Covoiturez-vous souvent ? CarpoX est un boîtier à mettre dans la voiture qui
mesure au GPS les km de chaque trajet et note qui était à bord grâce à des
badges RFID. Une app calcule ensuite qui doit combien à qui, en tenant compte
de qui a payé chaque plein.

## Comment ça marche

```
 Boîtier (Pico W)                     Serveur Linux                App web (téléphone / PC)
 GPS + badges RFID  ── WiFi connu ──▶  API + base SQLite  ◀── HTTPS ──  comptes, pleins, soldes
        ▲                                                                    │
        └──────────────────────── Bluetooth (BLE) ───────────────────────────┘
               synchro via le téléphone, association des badges
```

1. **Dans la voiture** : on badge le conducteur puis les passagers, et le
   boîtier compte les km au GPS jusqu'à l'arrivée.
2. **Synchronisation** : dès que le boîtier voit un WiFi connu (maison, partage
   de connexion), il envoie ses trajets au serveur. On peut aussi le faire via
   le téléphone en Bluetooth, depuis l'app.
3. **Au plein** : celui qui paie saisit le prix dans l'app. Le plein est réparti
   sur les trajets faits depuis le plein précédent.
4. **Soldes** : l'app affiche qui doit combien à qui, avec le minimum de
   virements. On y note aussi les remboursements, péages et parkings.

### Règle de partage

Chaque trajet coûte `km du trajet × prix au km du plein`, partagé à parts
égales entre les personnes à bord, conducteur compris. Un trajet fait seul est
payé par le conducteur ; un trajet à quatre coûte un quart à chacun. Si le
compteur journalier indique plus de km que les trajets enregistrés, la
différence reste à la charge de celui qui a payé le plein. Les calculs se font
au centime près, sans jamais perdre ni créer de centime.

## Organisation du dépôt

| Dossier | Contenu |
|---|---|
| [`core/`](core/) | Logique partagée en Python pur : distances GPS, répartition des frais, soldes, import de l'ancien historique. Tourne sur le serveur et sur le Pico. |
| [`firmware/`](firmware/) | MicroPython pour le Raspberry Pi Pico W : écrans, GPS, badges, WiFi, Bluetooth. |
| [`server/`](server/) | Serveur FastAPI + SQLite : comptes, synchro, calcul des soldes. Sert aussi l'app. |
| [`app/`](app/) | App web installable (HTML/JS sans dépendance) : comptes, pleins, soldes, Bluetooth. |
| [`hardware/`](hardware/) | Brochage, schémas Fritzing, boîtier 3D, liste du matériel. |

## Démarrer

- Serveur et app : voir [`server/README.md`](server/README.md).
- Boîtier : voir [`firmware/README.md`](firmware/README.md) et
  [`hardware/README.md`](hardware/README.md).

L'app fonctionne dans tout navigateur. Le Bluetooth depuis l'app demande
Chrome ou Edge (Android, Windows, macOS, Linux) ; il n'est pas disponible sur
iPhone, où la synchro passe alors uniquement par le WiFi du boîtier.

## Tests

```bash
pip install -r server/requirements-dev.txt
pytest
```

Les tests couvrent la logique de partage, le firmware (avec une simulation du
matériel qui envoie de vraies trames GPS) et l'API du serveur.

## Crédits

@LaTeam — Julien Dagnelie & Loïc Tumelaire (UCLouvain).
