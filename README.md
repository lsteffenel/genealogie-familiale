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

## Interface membre

- `/` : liste des personnes avec recherche
- `/personne/<id>/` : fiche complète (famille, unions, enfants, parcours, photos, historique des propositions)
- `/personne/<id>/proposer/` : formulaire de proposition de modification (validée par un modérateur)
- `/propositions/` : file de modération (réservée aux modérateurs)
- Connexion requise pour tout le site (`/connexion/`)

## Roadmap

1. Fondations : modèles, rôles, import GEDCOM, modération
2. Interface membre : consultation de l'arbre, soumission de propositions
3. Intégration Google Photos (API, lecture seule)
4. Déploiement

## Tests

```bash
python manage.py test
```
