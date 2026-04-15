# Processus de Déploiement - TontineApp

## Prérequis

- Python 3.13+
- Docker & Docker Compose
- PostgreSQL 15+ (si déploiement sans Docker)
- Redis 7+ (pour les tâches de fond)

---

## 1. Développement Local avec Docker

```bash
# Cloner et configurer
cp .env.example .env
# Éditer .env avec vos valeurs

# Démarrer l'application
docker-compose up --build

# L'application sera accessible sur http://localhost:8000
```

Les services démarrés:
- **web**: Application Django (port 8000)
- **db**: PostgreSQL 15 (port 5432)
- **redis**: Redis 7 (port 6379)

---

## 2. Déploiement sur Serveur (Production)

### Option A: Docker Compose (Recommandé)

```bash
# 1. Installer Docker et Docker Compose sur le serveur

# 2. Cloner le projet
git clone <repo-url> tontine-app
cd tontine-app

# 3. Configurer l'environnement
cp .env.example .env
nano .env  # Configurer les variables de production

# 4. Construire et démarrer
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 5. Appliquer les migrations
docker-compose exec web python manage.py migrate

# 6. Collecter les fichiers statiques
docker-compose exec web python manage.py collectstatic --noinput
```

### Option B: Déploiement Manuel

```bash
# 1. Préparer l'environnement
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Configurer PostgreSQL
# Créer la base de données et l'utilisateur

# 4. Configurer Redis
# Installer et démarrer Redis

# 5. Configurer les variables d'environnement
export DJANGO_DEBUG=False
export DJANGO_SECRET_KEY=<generated-secret-key>
export DATABASE_URL=postgres://user:password@localhost:5432/tontinedb
export REDIS_URL=redis://localhost:6379/0

# 6. Appliquer les migrations
python manage.py migrate

# 7. Collecter les fichiers statiques
python manage.py collectstatic --noinput

# 8. Démarrer avec Gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

---

## 3. Déploiement sur Platform-as-a-Service

### Heroku / Render / Railway

Utiliser le `Procfile`:

```bash
# Heroku
heroku create tontine-app
heroku addons:create heroku-postgresql:mini
heroku addons:create heroku-redis
heroku config:set DJANGO_DEBUG=False
heroku config:set DJANGO_SECRET_KEY=<secret>
git push heroku main
```

Le `Procfile` configure:
- `web`: Gunicorn (2 workers, 4 threads)
- `worker`: Django-Q pour les tâches asynchrones
- `beat`: Scheduler Django-Q pour les tâches périodiques

---

## 4. Configuration Production Critique

### Variables d'environnement obligatoires

```env
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<clé-unique-64-caractères>
DJANGO_ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com
DATABASE_URL=postgres://user:pass@host:5432/tontinedb
REDIS_URL=redis://localhost:6379/0
```

### Générer une clé secrète

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Commandes post-déploiement

```bash
# Migrer la base de données
python manage.py migrate

# Créer un superutilisateur
python manage.py createsuperuser

# Collecter les fichiers statiques
python manage.py collectstatic --noinput

# Redémarrer les services
sudo systemctl restart tontine-app
```

---

## 5. Tâches de Fond (Workers)

L'application utilise Django-Q pour:
- Envoi de SMS asynchrones
- Génération de rapports PDF
- Notifications programmées

```bash
# Démarrer le worker
python manage.py qcluster

# Démarrer le scheduler (beat)
python manage.py qbeat
```

---

## 6. Monitoring

### Logs Docker

```bash
docker-compose logs -f web
docker-compose logs -f worker
```

### Vérifier la santé

```bash
curl http://localhost:8000/health/
```

---

## 7. Mises à jour

```bash
# Pull les dernières modifications
git pull origin main

# Reconstruire et redémarrer
docker-compose down
docker-compose up --build -d

# OU pour une mise à jour sans downtime
docker-compose up --build -d --no-deps web
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py collectstatic --noinput
```
