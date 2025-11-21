import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "league_app.settings")
django.setup()

from django.conf import settings
from django.contrib.staticfiles import finders

print("="*50)
print("DEBUG: FINDERS DIAGNOSTIC (STRICT MODE)")
print("="*50)

print(f"DEBUG: STATIC_ROOT = {settings.STATIC_ROOT}")
print(f"DEBUG: STATICFILES_DIRS = {settings.STATICFILES_DIRS}")
print(f"DEBUG: STATICFILES_FINDERS = {settings.STATICFILES_FINDERS}")

print("\n1. Testing get_finders() (Exact collectstatic logic):")
all_finders = list(finders.get_finders())
print(f"   Found {len(all_finders)} finders: {[f for f in all_finders]}")

total_files = 0
for finder in all_finders:
    print(f"\n   Scanning finder: {finder}...")
    try:
        # collectstatic calls list(ignore_patterns)
        # We pass None to ignore_patterns for now, or empty list
        count = 0
        for path, storage in finder.list(ignore_patterns=None):
            print(f"      - Found: {path}")
            count += 1
            total_files += 1
            if count >= 5:
                print("      ... (stopping output after 5, but continuing count)")
        print(f"   -> Finder found {count} files.")
    except Exception as e:
        print(f"   ERROR in finder {finder}: {e}")

print(f"\nTotal files found by all finders: {total_files}")

if total_files == 0:
    print("\nCRITICAL: get_finders() returned NO files. This explains why collectstatic fails.")
else:
    print("\nSUCCESS: Finders are working. If collectstatic fails, it's a storage/writing issue.")

print("="*50)
print(f"DEBUG: Active STATICFILES_STORAGE = {settings.STATICFILES_STORAGE}")
print(f"DEBUG: Active STORAGES = {settings.STORAGES}")
import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "league_app.settings")
django.setup()

from django.conf import settings
from django.contrib.staticfiles import finders

print("="*50)
print("DEBUG: FINDERS DIAGNOSTIC (STRICT MODE)")
print("="*50)

print(f"DEBUG: STATIC_ROOT = {settings.STATIC_ROOT}")
print(f"DEBUG: STATICFILES_DIRS = {settings.STATICFILES_DIRS}")
print(f"DEBUG: STATICFILES_FINDERS = {settings.STATICFILES_FINDERS}")

print("\n1. Testing get_finders() (Exact collectstatic logic):")
all_finders = list(finders.get_finders())
print(f"   Found {len(all_finders)} finders: {[f for f in all_finders]}")

total_files = 0
for finder in all_finders:
    print(f"\n   Scanning finder: {finder}...")
    try:
        # collectstatic calls list(ignore_patterns)
        # We pass None to ignore_patterns for now, or empty list
        count = 0
        for path, storage in finder.list(ignore_patterns=None):
            print(f"      - Found: {path}")
            count += 1
            total_files += 1
            if count >= 5:
                print("      ... (stopping output after 5, but continuing count)")
        print(f"   -> Finder found {count} files.")
    except Exception as e:
        print(f"   ERROR in finder {finder}: {e}")

print(f"\nTotal files found by all finders: {total_files}")

if total_files == 0:
    print("\nCRITICAL: get_finders() returned NO files. This explains why collectstatic fails.")
else:
    print("\nSUCCESS: Finders are working. If collectstatic fails, it's a storage/writing issue.")

print("="*50)
print(f"DEBUG: Active STATICFILES_STORAGE = {settings.STATICFILES_STORAGE}")
print(f"DEBUG: Active STORAGES = {settings.STORAGES}")

from django.core.management import call_command
print("\n5. Running collectstatic programmatically via call_command:")
try:
    call_command('collectstatic', interactive=False, clear=True, verbosity=2)
except Exception as e:
    print(f"   ERROR running collectstatic: {e}")

print("="*50)
print("6. Inspecting collectstatic command:")
from django.core.management import get_commands, load_command_class
try:
    commands = get_commands()
    app_name = commands['collectstatic']
    print(f"   'collectstatic' is provided by app: {app_name}")
    cmd_class = load_command_class(app_name, 'collectstatic')
    print(f"   Command class: {cmd_class}")
except Exception as e:
    print(f"   ERROR inspecting command: {e}")

print("="*50)
print("7. Testing STATIC_ROOT permissions:")
import shutil
try:
    if not os.path.exists(settings.STATIC_ROOT):
        print(f"   Creating STATIC_ROOT: {settings.STATIC_ROOT}")
        os.makedirs(settings.STATIC_ROOT)
    
    test_file = os.path.join(settings.STATIC_ROOT, 'test_write.txt')
    with open(test_file, 'w') as f:
        f.write("Write test successful.")
    print(f"   SUCCESS: Wrote to {test_file}")
    os.remove(test_file)
except Exception as e:
    print(f"   ERROR writing to STATIC_ROOT: {e}")

print("="*50)
