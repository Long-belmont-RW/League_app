import os
import shutil
import sys
import django
from django.conf import settings
from django.contrib.staticfiles import finders

def manual_collect():
    print("="*50)
    print("STARTING MANUAL STATIC COLLECTION")
    print("="*50)
    
    # Setup Django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "league_app.settings")
    django.setup()

    static_root = settings.STATIC_ROOT
    if not os.path.exists(static_root):
        os.makedirs(static_root)
        print(f"Created STATIC_ROOT: {static_root}")

    print(f"Target Directory: {static_root}")

    copied_count = 0
    ignored_count = 0
    error_count = 0

    # Iterate through all finders (FileSystemFinder, AppDirectoriesFinder, etc.)
    for finder in finders.get_finders():
        print(f"\nScanning using finder: {finder.__class__.__name__}")
        
        try:
            # List all files found by this finder
            for path, storage in finder.list(ignore_patterns=None):
                try:
                    # Get the absolute source path
                    # Note: This works for FileSystemStorage, which is what finders use locally
                    if hasattr(storage, 'path'):
                        source_path = storage.path(path)
                    else:
                        print(f"  [SKIP] Storage for {path} does not support .path()")
                        continue

                    # EXCLUSION LOGIC
                    # User requested to avoid overwriting with Tailwind files from 'theme' app
                    # We check if the source path contains 'theme/static'
                    # Normalize separators for cross-platform check
                    normalized_source = source_path.replace("\\", "/")
                    
                    if "/theme/static/" in normalized_source or "/theme/static_src/" in normalized_source:
                        # print(f"  [IGNORE] Tailwind file: {path}")
                        ignored_count += 1
                        continue

                    # Destination path
                    dest_path = os.path.join(static_root, path)
                    dest_dir = os.path.dirname(dest_path)

                    # Create parent directories if needed
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)

                    # Copy file
                    # copy2 preserves metadata
                    shutil.copy2(source_path, dest_path)
                    copied_count += 1
                    
                    # Verbose output for first few files or specific ones
                    if copied_count <= 5 or "admin" in path:
                        # print(f"  [COPY] {path}")
                        pass

                except Exception as e:
                    print(f"  [ERROR] Failed to copy {path}: {e}")
                    error_count += 1

        except Exception as e:
            print(f"Error listing files for finder {finder}: {e}")

    print("="*50)
    print(f"MANUAL COLLECTION FINISHED")
    print(f"Files Copied: {copied_count}")
    print(f"Files Ignored (Tailwind): {ignored_count}")
    print(f"Errors: {error_count}")
    print("="*50)

if __name__ == "__main__":
    manual_collect()
