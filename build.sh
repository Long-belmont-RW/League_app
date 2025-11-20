#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt


# Ignore BOTH cloudinary and admin files during collection/compression
python manage.py collectstatic --no-input --clear --ignore=cloudinary* --ignore=admin*
python manage.py migrate
