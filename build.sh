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

echo "Collecting static files..."
python manage.py collectstatic --no-input --clear

# 5. Run Migrations
echo "Running migrations..."
python manage.py migrate
