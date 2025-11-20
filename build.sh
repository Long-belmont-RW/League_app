#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# The --clear flag deletes the existing staticfiles folder before copying
python manage.py collectstatic --no-input --clear --ignore=cloudinary*
python manage.py migrate
