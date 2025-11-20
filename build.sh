#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt


# We add --ignore=svg/* to skip compressing SVGs, which often cause this specific crash
python manage.py collectstatic --no-input --clear --ignore=cloudinary* --ignore=admin* --ignore=*.svg
python manage.py migrate
