# Serveur CarpoX

API + base de données pour les boîtiers et l'app. Python 3.10+, FastAPI,
SQLite (un seul fichier, rien d'autre à installer).

## Ce qu'il fait

- **Comptes** : mots de passe hachés avec scrypt, sessions par jeton aléatoire
  (seule l'empreinte est stockée), blocage 15 min après 5 échecs, code
  d'invitation optionnel pour empêcher les inscriptions inconnues.
- **Voitures** : chaque boîtier est une voiture partagée par des membres. Le
  propriétaire reçoit un jeton de boîtier (affiché une seule fois) et un code
  Bluetooth à 6 chiffres.
- **Synchro** : `POST /api/device/sync` reçoit les trajets du boîtier en WiFi,
  `POST /api/devices/{id}/relay` les reçoit via l'app (Bluetooth). Les deux sont
  idempotents : un trajet renvoyé n'est jamais compté deux fois.
- **Comptes entre personnes** : pleins, frais partagés (péage, parking) et
  remboursements saisis dans l'app ; `GET /api/devices/{id}/summary` renvoie les
  soldes et les virements proposés, calculés par `core/carpox_core`.
- Sert aussi l'app web (`app/`) à la racine du site.

Documentation interactive de l'API : `/api/docs`.

## Lancer en local

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r server/requirements-dev.txt
PYTHONPATH=core:server uvicorn carpox_server.main:app --reload
# puis http://localhost:8000
```

Tests : `pytest` à la racine du dépôt.

## Installer sur un serveur Linux (Debian/Ubuntu)

```bash
sudo useradd --system --home /opt/carpox carpox
sudo git clone https://github.com/Kenderium/Compteur-km-covoiturage /opt/carpox
sudo python3 -m venv /opt/carpox/.venv
sudo /opt/carpox/.venv/bin/pip install -r /opt/carpox/server/requirements.txt
sudo mkdir -p /var/lib/carpox && sudo chown carpox /var/lib/carpox
sudo cp /opt/carpox/server/deploy/carpox.service /etc/systemd/system/
sudo systemctl enable --now carpox
```

Puis un reverse proxy HTTPS devant (exemple Caddy dans `deploy/Caddyfile`,
à adapter avec votre nom de domaine). Le HTTPS est indispensable : il protège
les mots de passe et le jeton du boîtier, et le Bluetooth web ne fonctionne que
sur une page HTTPS.

Sauvegarde : copier `/var/lib/carpox/carpox.sqlite3` (par exemple avec
`sqlite3 carpox.sqlite3 ".backup sauvegarde.sqlite3"`).
