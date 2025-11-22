#!/usr/bin/env bash
set -o errexit

# 1. Install Python Dependencies
pip install -r requirements.txt

# 2. Install Node.js (required for Tailwind)
# Render's native Python environment doesn't have Node.js, so we install it manually.
echo "Installing Node.js..."
NODE_VERSION=v20.11.0
NODE_DIST=node-$NODE_VERSION-linux-x64
curl -O https://nodejs.org/dist/$NODE_VERSION/$NODE_DIST.tar.xz
tar -xJvf $NODE_DIST.tar.xz
export PATH=$PWD/$NODE_DIST/bin:$PATH
export NPM_BIN_PATH=$PWD/$NODE_DIST/bin/npm
node -v
npm -v

# 3. Build Tailwind CSS
# We must install dependencies and build BEFORE collectstatic
echo "Building Tailwind CSS..."
python manage.py tailwind install
python manage.py tailwind build

# 4. Collect Static Files
# We use --no-input to avoid prompts
# We clear the existing directory to ensure a clean build
# Debug: Check if static files exist
echo "Current directory: $PWD"
ls -la
echo "Listing static directory:"
ls -R static || echo "Static directory not found"

echo "Running Finders Diagnostic..."
python debug_finders.py

echo "Collecting static files..."
python manage.py collectstatic --no-input --clear -v 2

# Fallback: If collectstatic failed to populate staticfiles, copy manually
if [ -z "$(ls -A staticfiles 2>/dev/null)" ] || [ "$(ls -A staticfiles | wc -l)" -eq 0 ]; then
    echo "WARNING: collectstatic failed to copy files. Attempting manual copy..."
    mkdir -p staticfiles
    
    # Copy project static files
    if [ -d "static" ]; then
        echo "Copying static/..."
        cp -r static/* staticfiles/
    fi
    
    # Copy Tailwind static files
    # if [ -d "theme/static" ]; then
    #     echo "Copying theme/static/..."
    #     cp -r theme/static/* staticfiles/
    # fi
    
    echo "Manual copy completed."
    ls -R staticfiles
else
    echo "collectstatic successfully populated staticfiles."
fi

# 5. Run Migrations
echo "Running migrations..."
python manage.py migrate
