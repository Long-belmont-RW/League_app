#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt


# The critical part is --no-post-process
python manage.py collectstatic --no-input --clear --no-post-process
python manage.py migrate
