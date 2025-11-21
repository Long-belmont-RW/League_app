#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

# FORCE DELETE the actual staticfiles directory used by Render
rm -rf /opt/render/project/src/staticfiles

# Build fresh static files
python manage.py collectstatic --no-input

python manage.py migrate
