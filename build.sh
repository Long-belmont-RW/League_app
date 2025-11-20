#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# --- TAILWIND DISABLED (Using the file we committed instead) ---
# python manage.py tailwind install
# python manage.py tailwind build
# ---------------------------------------------------------------

# Collect static files
python manage.py collectstatic --no-input --clear --no-post-process --ignore=cloudinary* --ignore=admin* --ignore=*.svg

python manage.py migrate