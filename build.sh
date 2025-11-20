#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Install Python dependencies
pip install -r requirements.txt




# 3. Collect Static Files (with our safety flags)
python manage.py collectstatic --no-input --clear --no-post-process --ignore=cloudinary* --ignore=admin* --ignore=*.svg

# 2. Install Node dependencies & Build Tailwind (Required for styles.css)
python manage.py tailwind install
python manage.py tailwind build

# 4. Run Migrations
python manage.py migrate