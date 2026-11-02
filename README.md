# Généalogie familiale

Site collaboratif pour reprendre et compléter l'arbre généalogique familial
(export Geneanet / GEDCOM), avec ajout d'informations par les membres et
validation par un modérateur.

## Stack

- Python 3.12 / Django 5.1
- SQLite en développement, PostgreSQL recommandé en production

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_SECRET_KEY=une-cle-secrete-longue  # voir .env.example
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

L'administration (gestion des rôles, modération des propositions) se fait via
`/admin/`.

## Avec Docker (docker compose)

```bash
cp .env.example .env   # puis éditer les valeurs (mot de passe PostgreSQL obligatoire)
docker compose up --build
```

Le site est alors disponible sur http://localhost:8000 et la base PostgreSQL
persiste dans le volume `db_data`. En production, le conteneur `web` sert
l'application via gunicorn (voir `Dockerfile`) ; en compose de développement,
la commande est remplacée par `runserver` avec rechargement à chaud.

Pour importer l'export GEDCOM dans le conteneur :

```bash
docker compose exec web python manage.py import_gedcom /app/export.ged
```

## Import de l'export Geneanet (GEDCOM)

```bash
python manage.py import_gedcom chemin/vers/export.ged          # import réel
python manage.py import_gedcom chemin/vers/export.ged --dry-run  # test à blanc
```

## Modèle de données

- **Person** : identité, sexe, naissance/décès, biographie, photo (upload ou Google Photos)
- **Union** : mariage/PACS/concubinage entre deux personnes, enfants associés
- **Event** : informations tierces (diplôme, métier, résidence, anecdote, distinction)
- **Media** : photos rattachées à une personne ou un événement (upload ou Google Photos)
- **EditProposal** : proposition de modification soumise par un membre, approuvée/rejetée par un modérateur
- **Profile** : rôle de l'utilisateur (membre, modérateur, administrateur)

## Google Photos (lecture seule)

Les fiches peuvent référencer des photos de l'album Google Photos partagé via
leur `media item ID` (champ `google_photo_media_item_id` sur `Person` et `Media`).

Configuration (dans `.env`) :

```
GOOGLE_PHOTOS_CLIENT_ID=...
GOOGLE_PHOTOS_CLIENT_SECRET=...
GOOGLE_PHOTOS_REFRESH_TOKEN=...
```

Obtention du refresh token (une seule fois, depuis un poste ayant accès au compte Google) :

```bash
python - <<'EOF'
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_config(
    {"installed": {"client_id": "VOTRE_CLIENT_ID", "client_secret": "VOTRE_SECRET",
                   "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                   "token_uri": "https://oauth2.googleapis.com/token",
                   "redirect_uris": ["http://localhost"]}},
    scopes=["https://www.googleapis.com/auth/photospicker.mediaitems.readonly"],
)
creds = flow.run_local_server(port=0)
print(creds.refresh_token)
EOF
```

Le scope utilisé est `photospicker.mediaitems.readonly` : accès strictement en
lecture aux médias sélectionnés via le sélecteur Google Photos. Sans ces
variables, le site affiche un simple libellé à la place des photos. Les URL
signées retournées par l'API sont mises en cache 6 h.

## Confidentialité et RGPD

- **Aucune donnée personnelle n'est accessible sans connexion** : liste des
  personnes, fiches, propositions et médias exigent tous un compte authentifié
  (testé automatiquement, y compris pour `/media/...`).
- La page de connexion est la seule page publique.
- L'administration Django (`/admin/`) est réservée au staff ; la modération des
  propositions est réservée au rôle modérateur.
- En production, servez les médias (`/media/`) derrière une authentification
  (proxy inverse avec contrôle d'accès, ou vue authentifiée comme en DEBUG) :
  ne les exposez jamais publiquement.
- Pensez à purger les données des comptes supprimés et à documenter la durée
  de conservation conforme au RGPD.

## Interface membre

- `/` : liste des personnes avec recherche
- `/personne/<id>/` : fiche complète (famille, unions, enfants, parcours, photos, historique des propositions)
- `/personne/<id>/proposer/` : formulaire de proposition de modification (validée par un modérateur)
- `/propositions/` : file de modération (réservée aux modérateurs)
- `/arbre/` : **arbre graphique** avec choix de la racine et cases à cocher
  pour afficher/masquer nom, dates et photo (paramètres `?name=0&dates=0&photo=0`)
- Connexion requise pour tout le site (`/connexion/`)

## Notifications e-mail

À chaque nouvelle proposition soumise par un membre, un e-mail est envoyé à
tous les modérateurs/administrateurs actifs ayant une adresse e-mail.
Configuration via `EMAIL_BACKEND`, `DEFAULT_FROM_EMAIL` et, pour le SMTP,
`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
`EMAIL_USE_TLS` (console par défaut en développement, voir `.env.example`).

## Roadmap

1. Fondations : modèles, rôles, import GEDCOM, modération
2. Interface membre : arbre graphique, soumission de propositions
3. Intégration Google Photos (API, lecture seule)
4. Notifications e-mail des modérateurs
5. Déploiement

## Tests

```bash
python manage.py test
```
