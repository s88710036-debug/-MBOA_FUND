#!/bin/bash
set -e

echo "=== TontineApp Build Script ==="

echo "[1/5] Installation des dépendances..."
pip install -r requirements.txt

echo "[2/5] Migration de la base de données..."
python manage.py migrate --noinput

echo "[3/5] Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

echo "[4/5] Création du superutilisateur (optionnel)..."
read -p "Voulez-vous créer un superutilisateur ? (o/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Oo]$ ]]; then
    python manage.py createsuperuser
fi

echo "[5/5] Démarrage du serveur..."
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4

echo "=== Terminé ==="
