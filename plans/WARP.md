# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project overview
- Django 5 project with Channels, django-allauth, and Tailwind CSS.
- Project module: league_app (settings, urls, ASGI/WSGI).
- First-party apps: users, league, content, fantasy, theme (for Tailwind).
- Database: SQLite in development.

Common commands (PowerShell on Windows)
- Create and activate a virtualenv, then install dependencies:
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```
- Apply migrations and create a superuser:
  ```powershell
  python manage.py migrate
  python manage.py createsuperuser
  ```
- Run the development server:
  ```powershell
  python manage.py runserver
  ```
- Tailwind CSS (theme app) for styles:
  - Start Tailwind dev watcher (during development):
    ```powershell
    python manage.py tailwind start
    ```
  - Build Tailwind assets (before collectstatic/production):
    ```powershell
    python manage.py tailwind build
    ```
- Collect static files (e.g., when preparing a build):
  ```powershell
  python manage.py collectstatic
  ```
- Run all tests (Django test runner):
  ```powershell
  python manage.py test
  ```
- Run tests for a single module or test case:
  ```powershell
  # module
  python manage.py test users.tests.test_auth_backend

  # specific test case
  python manage.py test users.tests.test_auth_backend.EmailRoleAuthBackendTests

  # specific test method
  python manage.py test users.tests.test_auth_backend.EmailRoleAuthBackendTests.test_authenticate_case_insensitive_email_and_role
  ```

Big-picture architecture
- Project configuration (league_app)
  - league_app/settings.py: INSTALLED_APPS includes users, league, content, fantasy, theme plus channels, debug_toolbar, django-allauth. AUTH_USER_MODEL is users.User. ASGI and WSGI apps configured. In-memory Channel layer configured for development. Static/media dirs configured. Logging configured to file and console.
  - league_app/urls.py: Root routes include:
    - '' -> league.urls (site home and league features)
    - 'fantasy/' -> fantasy.urls (namespaced)
    - 'accounts/' -> users.urls (custom auth and dashboards)
    - 'authentication/' -> allauth.urls (social login)
    - 'content/' -> content.urls
- Authentication and account flow
  - Custom user model (users/models.py: User) extends AbstractUser, uses email as USERNAME_FIELD, adds role (admin/player/coach/fan), birth, gender.
  - Custom auth backend (users/authentication.py: EmailRoleAuthBackend):
    - Case-insensitive email login.
    - Enforces unique-email semantics during authentication; duplicates are handled defensively with logging.
  - django-allauth integration with custom adapters (league/adapters.py):
    - CustomSocialAccountAdapter links verified provider emails to existing users, allows auto-signup; blocks ambiguous unverified conflicts with a redirect to login.
    - CustomAccountAdapter redirects post-login to profile completion if required fields (birth, gender) are missing.
- Users domain
  - Models (users/models.py): UserProfile one-to-one with User; optional links to league.Coach or league.Player. Notification model for simple per-user notifications.
  - Signals (users/signals.py):
    - On User save: create UserProfile; auto-create Coach/Player entity and link based on role.
    - On Coach/Player delete: cascade deletion of associated UserProfile and User (via explicit signal logic).
  - Views (users/views.py):
    - Email-based login, logout, register (supports invitation token), profile edit.
    - Role-gated dashboards for admin/coach/player/fan. Player/coach dashboards derive context from league models (latest league, upcoming/completed matches, stats, team table, lineup presence).
  - Utilities (users/utils.py):
    - push_user_notification: helper using Channels group_send (in-memory layer in dev).
    - get_season_progress: computes season completion percentage from matches.
- League domain
  - Core entities (league/models.py):
    - Personel (abstract), Player, Coach; Team and League (season/session with active flag).
    - Match with status (Scheduled/Live/Finished/Cancelled), kickoff tracking, validation (duplicate fixture checks), helpers for current minute, winner, events.
    - Participation aggregates: PlayerSeasonParticipation, CoachSeasonParticipation, TeamSeasonParticipation with efficient aggregation (update_stats) and ordering by points/goals.
    - PlayerStats per match; MatchEvent; Lineup with through model LineupPlayer.
  - Views (league/views.py):
    - Home: recent matches and top scorers for active league.
    - Lists and detail pages: leagues, teams, league table, matches (with filtering, pagination, and HTMX partial rendering paths).
  - Forms (league/forms.py): MatchForm validation for active teams, PlayerStatsForm (validation for sane ranges), Lineup formset enforcing exactly 11 starters, MatchEventForm constrained to players in lineups.
  - Utilities (league/utils.py): get_league_standings to compute sorted table data.
  - Signals (league/signals.py): When users sign up/connect via social accounts, populate basic name fields from provider data.
- Content domain
  - Invitation model (content/models.py): Single-use team invitations with role, token, expiry; integrated into users.register_view to prefill role/email and automatically attach to team and league participation.
- Tailwind theme
  - TAILWIND_APP_NAME = 'theme' (settings). NPM_BIN_PATH set in settings for Windows; Tailwind assets are built/watched via Django Tailwind management commands.
- Channels
  - ASGI configured; CHANNEL_LAYERS uses in-memory backend for development. No Redis configured here; realtime helpers exist but persistent, multi-process websockets would require switching to a Redis channel layer and defining consumers.

Notes derived from repository state
- No repository-level linter/formatter or type-checking configuration is present (e.g., flake8/black/isort/mypy configs not found). Accordingly, there are no standard lint commands in this repo.
- Tests are implemented using Django's TestCase; prefer python manage.py test. pytest is present in requirements but pytest-django is not, so use Django's runner unless tooling is updated.
