import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "league_app.settings")
django.setup()

from django.conf import settings
from django.contrib.staticfiles import finders

print("="*50)
print("DEBUG: FINDERS DIAGNOSTIC")
print("="*50)

# 1. Check Specific Files
target_file = "images/league_banner.jpg"
print(f"1. Searching for specific file: '{target_file}'")
found = finders.find(target_file)
print(f"   Found at: {found}")

admin_file = "admin/css/base.css"
print(f"2. Searching for admin file: '{admin_file}'")
found_admin = finders.find(admin_file)
print(f"   Found at: {found_admin}")

# 2. Test FileSystemFinder
print("\n3. Testing FileSystemFinder explicitly:")
try:
    fs_finder = finders.FileSystemFinder()
    count = 0
    for path, storage in fs_finder.list([]):
        print(f"   - Found: {path}")
        count += 1
        if count >= 5:
            print("   ... (stopping after 5)")
            break
    if count == 0:
        print("   WARNING: FileSystemFinder found NO files.")
except Exception as e:
    print(f"   ERROR in FileSystemFinder: {e}")

# 3. Test AppDirectoriesFinder
print("\n4. Testing AppDirectoriesFinder explicitly:")
try:
    app_finder = finders.AppDirectoriesFinder()
    count = 0
    for path, storage in app_finder.list([]):
        print(f"   - Found: {path}")
        count += 1
        if count >= 5:
            print("   ... (stopping after 5)")
            break
    if count == 0:
        print("   WARNING: AppDirectoriesFinder found NO files.")
except Exception as e:
    print(f"   ERROR in AppDirectoriesFinder: {e}")

print("="*50)
