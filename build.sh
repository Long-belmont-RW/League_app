#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# The --no-post-process flag tells WhiteNoise: "Just copy the files, don't compress them."
# This prevents all FileNotFoundError crashes during compression.
python manage.py collectstatic --no-input --clear --no-post-process
python manage.py migrate
