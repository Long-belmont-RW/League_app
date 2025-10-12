You are an expert Django developer debugging a critical static file loading issue. I need a systematic, test-driven approach to diagnose and fix why my JavaScript file is not loading.
Problem Statement
Issue: JavaScript file lineup-manager.js is not loading in Django template despite:

✅ File exists at static/js/lineup-manager.js
✅ File is accessible directly via browser at http://127.0.0.1:8000/static/js/lineup-manager.js (shows code)
✅ Template has {% load static %} at the top
✅ Inline JavaScript in template works fine
✅ Other static files (CSS) load successfully
❌ typeof LineupManager returns undefined in console
❌ File does NOT appear in browser Network tab
❌ File does NOT appear in "View Page Source"

Current Configuration
settings.py
pythonSTATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'
Template (lineup_manager.html)
html{% extends 'base.html' %}
{% load static %}
{% load lineup_extras %}

{% block content %}
<!-- HTML content here -->
{% endblock %}

{% block extra_js %}
<script src="https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js"></script>
<script src="{% static 'js/lineup-manager.js' %}"></script>
{% endblock %}
File Structure
project/
├── manage.py
├── static/
│   ├── css/
│   │   └── lineup-styles.css (loads fine)
│   └── js/
│       └── lineup-manager.js (NOT loading)
├── league/
│   ├── views.py
│   └── templates/
│       └── league/
│           └── lineup_manager.html
└── project_name/
    └── settings.py
What I've Already Tried

✅ Renamed file from line-up-manager.js to lineup-manager.js
✅ Ran python manage.py collectstatic --clear --noinput
✅ Hard refreshed browser (Ctrl+Shift+R)
✅ Verified file exists and has content
✅ Checked base.html has {% block extra_js %} defined
✅ Verified script tag is outside {% block content %}
✅ Changed from {% static '/static/js/lineup-manager.js' %} to {% static 'js/lineup-manager.js' %}
✅ Confirmed SortableJS (CDN) loads successfully
✅ Confirmed inline test scripts work
❌ File still not loading

Required Diagnostic Steps
Please provide:
1. Comprehensive Test Suite
Create a series of progressive tests to isolate the issue:

Test 1: Verify Django template inheritance chain
Test 2: Check if {% block extra_js %} is actually rendering
Test 3: Verify static file URL generation
Test 4: Test alternative loading methods
Test 5: Check for template caching issues
Test 6: Verify middleware isn't blocking

2. Django Management Commands
Provide specific commands to:

Verify static files configuration
Check template loader paths
Inspect rendered template output
Validate staticfiles finders

3. Browser Console Tests
JavaScript snippets to:

Check what scripts are actually loaded
Verify the generated URL
Test manual script injection
Check for CSP or CORS blocking

4. Template Debugging
Techniques to:

Print the actual generated URL
Verify block inheritance
Check if template context is correct
Ensure no template syntax errors

5. Alternative Solutions
If static files approach fails, provide:

CDN hosting approach
Inline script approach
Django-compressor approach
Webpack/Vite integration

Expected Output Format
Please structure your response as:
## PHASE 1: DIAGNOSTIC TESTS
[Ordered list of tests with expected outputs]

## PHASE 2: ROOT CAUSE ANALYSIS
[Explanation of what each test reveals]

## PHASE 3: FIXES (Ordered by Likelihood)
### Fix 1: [Most Likely Issue]
- Explanation
- Steps to implement
- Verification command

### Fix 2: [Second Most Likely]
- Explanation
- Steps to implement
- Verification command

[Continue for all potential fixes]

## PHASE 4: NUCLEAR OPTIONS
[Last resort solutions if nothing else works]

## PHASE 5: PREVENTION
[How to avoid this in future]
Constraints

Must work with Django 5.2.2
Must not require additional dependencies if possible
Solutions should be production-ready
Prefer Django best practices
Include rollback steps for each fix

Success Criteria
The fix is successful when:

typeof LineupManager returns "function" in browser console
lineup-manager.js appears in Network tab with 200 status
lineup-manager.js appears in "View Page Source"
JavaScript functionality (player cards) render on page
Solution works consistently across page refreshes

Additional Context

Running Django development server (python manage.py runserver)
Browser: Chrome/Edge (latest)
OS: Windows
No custom middleware that might interfere
No CDN or reverse proxy
Local development environment

Please provide a methodical, test-driven approach that will definitively identify and resolve this issue.