# Déploiement en production (Docker + Apache)

Ce guide déploie le site sur `genealogia.lsteffenel.fr`, derrière le reverse proxy
Apache déjà en place (même principe que `urca.lsteffenel.fr`), avec PostgreSQL en
conteneur. Le conteneur web n'est exposé que sur `127.0.0.1:8001` (le port 8000 est
déjà utilisé par l'autre site).

## 1. Préparer le serveur

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin apache2 certbot python3-certbot-apache
sudo systemctl enable --now docker
sudo a2enmod proxy proxy_http
```

## 2. Récupérer le code et configurer `.env`

```bash
sudo mkdir -p /opt/genealogie && sudo chown $USER /opt/genealogie
cd /opt/genealogie
git clone https://github.com/lsteffenel/genealogie-familiale.git .
cp .env.example .env
```

Éditer `.env` (production) :

```bash
DJANGO_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=genealogia.lsteffenel.fr
POSTGRES_DB=genealogie
POSTGRES_USER=genealogie
POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend   # optionnel
# GOOGLE_PHOTOS_CLIENT_ID / SECRET / REFRESH_TOKEN quand l'API sera validée
```

## 3. Lancer les conteneurs

```bash
cd /opt/genealogie
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
# importer l'export GEDCOM si besoin :
#   cp /chemin/steffenel.ged /opt/genealogie/export.ged   # puis monter ou copier dans le conteneur
docker compose -f docker-compose.prod.yml exec web python manage.py import_gedcom /app/export.ged --dry-run
```

Au démarrage, le conteneur exécute automatiquement `migrate` + `collectstatic` puis
gunicorn (voir `docker-compose.prod.yml`).

## 4. Vhost Apache

`/etc/apache2/sites-available/genealogia.conf` :

```apache
<VirtualHost *:80>
    ServerName genealogia.lsteffenel.fr

    ProxyPreserveHost On
    ProxyPass / http://localhost:8001/
    ProxyPassReverse / http://localhost:8001/

    ErrorLog ${APACHE_LOG_DIR}/genealogia_error.log
    CustomLog ${APACHE_LOG_DIR}/genealogia_access.log combined
</VirtualHost>
```

```bash
sudo a2ensite genealogia
sudo systemctl reload apache2
sudo certbot --apache -d genealogia.lsteffenel.fr   # passe le vhost en HTTPS (redirection auto)
```

## 5. Vérifications

- http://genealogia.lsteffenel.fr redirige vers HTTPS et affiche la page de connexion.
- `/admin/` fonctionne (CSS servi par WhiteNoise, `DEBUG=0`).
- Les médias (`/media/...`) restent derrière l'authentification Django
  (vue `login_required`), comme en développement.

## Notes

- Le volume `db_data` conserve la base PostgreSQL ; les médias uploadés sont dans `media_data`.
- Mises à jour : `git pull && docker compose -f docker-compose.prod.yml up -d --build`.
- Sauvegarde : `docker compose -f docker-compose.prod.yml exec db pg_dump -U genealogie genealogie > backup.sql`.
