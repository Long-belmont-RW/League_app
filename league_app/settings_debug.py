
# DEBUG: Print Static Files Configuration
import sys
print("="*50, file=sys.stderr)
print(f"DEBUG: BASE_DIR = {BASE_DIR}", file=sys.stderr)
print(f"DEBUG: STATIC_ROOT = {STATIC_ROOT}", file=sys.stderr)
print(f"DEBUG: STATICFILES_DIRS = {STATICFILES_DIRS}", file=sys.stderr)
print(f"DEBUG: STATICFILES_FINDERS = {getattr(sys.modules[__name__], 'STATICFILES_FINDERS', 'NOT SET')}", file=sys.stderr)
print(f"DEBUG: INSTALLED_APPS = {INSTALLED_APPS}", file=sys.stderr)
print("="*50, file=sys.stderr)
