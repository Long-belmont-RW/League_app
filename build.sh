#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# 1. Manually delete the folder to force a fresh start
rm -rf staticfiles

# 2. Run collectstatic 
# We remove --no-post-process because we switched to the safer storage backend
# We keep --clear just in case
# We ignore admin/cloudinary/svg to prevent crashes
python manage.py collectstatic --no-input --clear --ignore=cloudinary* --ignore=admin* --ignore=*.svg

python manage.py migrate