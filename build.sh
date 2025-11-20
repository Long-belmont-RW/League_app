#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# 1. Build Tailwind (Crucial for styles.css)
python manage.py tailwind install
python manage.py tailwind build

# 2. Clean up old files
rm -rf staticfiles

# 3. Collect Static Files
# We keep --no-post-process to be safe against compression errors for now
python manage.py collectstatic --no-input --clear --no-post-process --ignore=cloudinary* --ignore=admin* --ignore=*.svg

python manage.py migrate