# CarpoX dans Home Assistant

L'intégration `carpox` affiche dans Home Assistant les km, le carburant estimé
et les soldes de vos voitures CarpoX. Elle lit le serveur CarpoX avec un
**jeton personnel en lecture seule** : elle ne peut rien modifier.

Chaque personne lie **son propre compte** CarpoX. Dans un Home Assistant
partagé, on peut ajouter plusieurs comptes (une entrée par compte). Attention :
dans Home Assistant, tous les utilisateurs d'une même instance voient les
mêmes capteurs. La séparation se fait par compte CarpoX, pas par utilisateur HA.

## Installation

### Avec HACS (conseillé)

1. HACS > menu ⋮ > **Dépôts personnalisés** : ajoutez
   `https://github.com/Kenderium/Compteur-km-covoiturage`, catégorie
   **Intégration**.
2. Installez **CarpoX**, puis redémarrez Home Assistant.

### À la main

Copiez le dossier `custom_components/carpox` de ce dépôt dans le dossier
`custom_components/` de votre configuration Home Assistant, puis redémarrez.

## Lier son compte

1. Dans l'app CarpoX, onglet **Compte** > **Home Assistant et autres
   applications** : donnez un nom au jeton (« Home Assistant maison ») et
   cliquez **Créer un jeton**. Copiez-le : il n'est affiché qu'une fois.
2. Dans Home Assistant : **Paramètres > Appareils et services > Ajouter une
   intégration > CarpoX**. Entrez l'adresse du serveur (celle de l'app, par
   exemple `https://carpox.mondomaine.be`) et le jeton.

Le jeton n'expire pas. Révoquez-le dans l'app quand il ne sert plus :
Home Assistant vous demandera alors un nouveau jeton. Changer de mot de passe
ne révoque pas les jetons.

La fréquence de mise à jour (10 minutes par défaut, de 5 à 60) se règle dans
les options de l'intégration.

## Ce que vous obtenez

Un appareil par voiture, avec :

| Capteur | Contenu |
|---|---|
| Km depuis le plein | km roulés depuis le dernier plein, avec ou sans badge |
| Carburant estimé | litres restants (attributs : réservoir, date et litres du dernier plein) |
| Niveau du réservoir estimé | en % |
| Autonomie estimée | km possibles avec le carburant restant |
| Consommation | L/100 km, mesurée grâce aux litres des pleins, sinon celle réglée par le propriétaire |
| Km totaux | tous les km comptés par le boîtier (attributs : avec et sans badge) |
| Km sans badge | km roulés sans que personne n'ait badgé |
| Compteur estimé | compteur de la voiture, si le propriétaire a donné le compteur à l'installation |
| Mes km | vos km dans cette voiture |
| Mon solde | ce que vous avez avancé (+) ou devez (−) ; attributs `je_dois` et `on_me_doit` |
| Remboursements à faire | nombre de virements proposés ; attributs `virements` (« Julien → Loïc : 12.50 € ») et `soldes` de tout le monde |
| Dernière synchro | quand le boîtier a envoyé ses trajets pour la dernière fois |
| Dernier trajet | km du dernier trajet (attributs : départ, arrivée, à bord) |
| Trajets | nombre de trajets |
| Dernière position | `device_tracker` : fin du dernier parcours GPS reçu que vous pouvez voir (le propriétaire voit tout, les autres membres seulement les trajets où ils étaient à bord) |

Et un appareil « CarpoX *votre nom* » avec votre solde total, ce que vous
devez, ce qu'on vous doit et vos km sur toutes les voitures.

### Estimation du carburant

Elle suppose que chaque plein remplit le réservoir. Le propriétaire indique
la capacité du réservoir et la consommation moyenne dans l'app (onglet
**Voiture**). Si on note les litres à chaque plein, la consommation réelle
est calculée sur les derniers pleins et remplace celle réglée. Le boîtier
compte les km dès qu'il est allumé, même si personne n'a badgé.

### Limites

- **Pas de position en direct** : le boîtier n'envoie ses trajets que
  lorsqu'il capte un WiFi connu (en général à la maison). La position et les
  km sont donc ceux de la dernière synchro.
- « Dernière synchro » récente veut souvent dire « voiture à la maison » :
  pratique pour les automatisations.

## Exemples

Carte de tableau de bord :

```yaml
type: entities
title: Golf
entities:
  - sensor.golf_carburant_estime
  - sensor.golf_autonomie_estimee
  - sensor.golf_km_depuis_le_plein
  - sensor.golf_mon_solde
  - sensor.golf_derniere_synchro
```

Rappel quand le réservoir est presque vide :

```yaml
automation:
  - alias: "Golf : faire le plein"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.golf_niveau_du_reservoir_estime
        below: 15
    actions:
      - action: notify.notify
        data:
          message: "Plus que {{ states('sensor.golf_autonomie_estimee') }} km d'autonomie dans la Golf."
```

Les noms exacts des entités dépendent du nom de la voiture et de la langue de
Home Assistant : vérifiez-les dans **Paramètres > Appareils et services >
CarpoX**.

## Sans l'intégration (capteur REST)

L'API est lisible directement : `GET /api/me/overview` avec l'en-tête
`Authorization: Bearer <jeton>`. Par exemple :

```yaml
rest:
  - resource: https://carpox.mondomaine.be/api/me/overview
    headers:
      Authorization: !secret carpox_token
    scan_interval: 600
    sensor:
      - name: "CarpoX solde"
        unit_of_measurement: "EUR"
        value_template: "{{ value_json.totals.balance_cents / 100 }}"
```

avec `carpox_token: "Bearer cpx_..."` dans `secrets.yaml`.

## Développement

Tests (Python 3.13) :

```bash
pip install -r home-assistant/requirements-test.txt
cd home-assistant && pytest
```

`tests/overview.json` est la réponse type du serveur. Les tests du serveur
vérifient qu'il renvoie bien ces clés, ce qui garde l'intégration et le
serveur d'accord.
