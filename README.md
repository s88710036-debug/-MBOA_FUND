# Tontine App

Application Django de gestion de tontines, contributions, tirages, notifications et paiements.

## Architecture du projet

- `manage.py` : point d'entrée Django.
- `config/` : configuration du projet, routes principales et WSGI.
- `apps/` : applications métier Django.
  - `accounts` : utilisateurs, rôles, profils, acceptation des CGU.
  - `tontines` : création et gestion des tontines, adhésions et cycles.
  - `contributions` : enregistrement et validation des contributions.
  - `draws` : tirages / distributions.
  - `notifications` : notifications et context processors.
  - `payments` : intégration Stripe, Orange Money, Wave, AfricasTalking.
  - `reports` : rapports, statistiques et dashboards.
- `static/` : fichiers CSS, JS, images.
- `templates/` : templates HTML.
- `tests/` : tests unitaires et de services.

## Structure recommandée

Le projet est organisé comme un monolithe Django fullstack : backend Python/Django + frontend via templates et assets statiques.

## Installation

1. Créez un environnement virtuel :

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Configurez les variables d'environnement dans `.env` ou votre environnement :

   - `DJANGO_SECRET_KEY`
   - `DJANGO_DEBUG`
   - `DJANGO_ALLOWED_HOSTS`
   - `DATABASE_URL` (optionnel)
   - `STRIPE_PUBLIC_KEY`
   - `STRIPE_SECRET_KEY`
   - `STRIPE_WEBHOOK_SECRET`
   - `ORANGE_MONEY_API_KEY`
   - `ORANGE_MONEY_MERCHANT_ID`
   - `ORANGE_MONEY_CALLBACK_URL`
   - `WAVE_API_KEY`
   - `WAVE_API_SECRET`
   - `WAVE_CALLBACK_URL`
   - `AFRICAS_TALKING_API_KEY`
   - `AFRICAS_TALKING_USERNAME`

3. Appliquez les migrations :

   ```powershell
   python manage.py migrate
   ```

4. Créez un super utilisateur :

   ```powershell
   python manage.py createsuperuser
   ```

5. Lancez le serveur de développement :

   ```powershell
   python manage.py runserver
   ```

## Tests

```powershell
python manage.py test
```

## Déploiement

- `Procfile` et `render.yaml` sont prêts pour un déploiement sur Render ou Heroku.
- `whitenoise` sert les fichiers statiques en production.
- `DATABASE_URL` permet d’utiliser PostgreSQL en lieu de SQLite.

## Notes importantes

- Le dossier `tontine-app/` et `tontine_project/` présents initialement étaient des duplicatas et ont été supprimés.
- La configuration `MOBILE_MONEY` a été nettoyée pour éviter les doublons.
- Le projet est désormais proprement structuré autour du dossier racine principal.
