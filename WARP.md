# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview
Django 5.2 web application for managing a sports league with fantasy league functionality. Uses SQLite in development, includes real-time features via Django Channels, social authentication via django-allauth, and Tailwind CSS for styling.

**Core apps**: `users`, `league`, `content`, `fantasy`, `theme` (Tailwind)

## Common Commands

### Environment Setup
```powershell
# Create and activate virtual environment
python -m venv myvenv
.\myvenv\Scripts\Activate.ps1
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Development Server
```powershell
# Run Django development server
python manage.py runserver

# Start Tailwind CSS watcher (run in separate terminal during development)
python manage.py tailwind start
```

### Testing
```powershell
# Run all tests
python manage.py test

# Run tests for specific app
python manage.py test users

# Run specific test module
python manage.py test users.tests.test_auth_backend

# Run specific test class
python manage.py test users.tests.test_auth_backend.EmailRoleAuthBackendTests

# Run specific test method
python manage.py test users.tests.test_auth_backend.EmailRoleAuthBackendTests.test_authenticate_case_insensitive_email_and_role
```

### Static Files
```powershell
# Build Tailwind CSS for production
python manage.py tailwind build

# Collect static files
python manage.py collectstatic
```

### Database Management
```powershell
# Create migrations after model changes
python manage.py makemigrations

# Show migration SQL
python manage.py sqlmigrate <app_name> <migration_number>

# Show unapplied migrations
python manage.py showmigrations
```

## Architecture

### Project Structure
- **league_app/**: Main project configuration (settings, urls, ASGI/WSGI)
- **users/**: Custom user model, authentication, role-based dashboards
- **league/**: Core league entities (teams, players, coaches, matches, standings)
- **fantasy/**: Fantasy league system with teams, transfers, scoring
- **content/**: Content management and team invitations
- **theme/**: Tailwind CSS configuration

### URL Routing (league_app/urls.py)
- `/` → league.urls (home, league features)
- `/fantasy/` → fantasy.urls (namespace: 'fantasy')
- `/accounts/` → users.urls (custom auth, dashboards)
- `/authentication/` → allauth.urls (social login)
- `/content/` → content.urls
- `/admin/` → Django admin

### Custom User System
**Model**: `users.User` (extends AbstractUser)
- Email-based authentication (USERNAME_FIELD = 'email')
- Roles: admin, player, coach, fan
- Additional fields: birth, gender, role
- One-to-one UserProfile with optional links to Player/Coach entities

**Authentication Backend**: `users.authentication.EmailRoleAuthBackend`
- Case-insensitive email login
- Enforces unique-email semantics with defensive duplicate handling

**Social Authentication**: django-allauth with custom adapters (league/adapters.py)
- `CustomSocialAccountAdapter`: Links verified provider emails to existing users, blocks ambiguous conflicts
- `CustomAccountAdapter`: Redirects to profile completion if birth/gender missing

### Users App
**Signals** (users/signals.py):
- Auto-creates UserProfile on User creation
- Auto-creates Coach/Player entity based on role
- Cascade deletion of UserProfile and User when Coach/Player deleted

**Views** (users/views.py):
- Email-based login, logout, registration (supports invitation tokens)
- Role-gated dashboards: admin, coach, player, fan
- Profile editing and completion

### League App
**Core Models** (league/models.py):
- `Personel` (abstract): Base for Player and Coach
- `League`: Season/session with year and session (Spring/Fall)
- `Team`: Teams with logos and bios
- `Match`: Matches with status (Scheduled/Live/Finished/Cancelled), scores, validation
- `PlayerSeasonParticipation`, `CoachSeasonParticipation`, `TeamSeasonParticipation`: Track performance per season
- `PlayerStats`: Per-match player statistics
- `MatchEvent`: Match events (goals, cards, substitutions, commentary)
- `Lineup`: Match lineups with starters and substitutes via LineupPlayer through model
- `TeamOfTheWeek`: Weekly best player selections

**Key Features**:
- Match validation prevents duplicate fixtures and teams playing themselves
- TeamSeasonParticipation.update_stats() efficiently aggregates match results
- Match.get_current_minute() calculates live match time from kickoff
- Standings ordered by points, goal difference, goals scored

**Forms** (league/forms.py):
- MatchForm: Validates active team participation
- PlayerStatsForm: Validates reasonable stat ranges
- Lineup formsets: Enforce exactly 11 starters
- MatchEventForm: Constrains events to players in match lineups

### Fantasy App
**Models** (fantasy/models.py):
- `FantasyLeague`: Configurable scoring rules, budget caps, transfer limits
- `FantasyTeam`: User's fantasy team with balance and player roster
- `FantasyPlayer`: Through model tracking purchase price, captain status
- `FantasyMatchWeek`: Weekly scoring periods with deadlines
- `FantasyPlayerStats`: Weekly point calculations with JSON breakdown
- `FantasyLeaderboard`: Rankings (weekly and overall)
- `FantasyTransfer`: Transfer history tracking

### Content App
**Invitation System** (content/models.py):
- Single-use team invitations with role, token, and expiry
- Integration with users.register_view for automatic team/league assignment

### Django Channels
- ASGI configured in league_app/asgi.py
- In-memory channel layer for development (channels.layers.InMemoryChannelLayer)
- Utility: `users.utils.push_user_notification` for real-time notifications
- **Note**: Production deployment requires Redis channel layer for persistent WebSocket connections

### Tailwind CSS
- Configured via django-tailwind package
- TAILWIND_APP_NAME = 'theme'
- NPM_BIN_PATH configured for Windows in settings.py
- Styles compiled via `python manage.py tailwind start` or `tailwind build`

### Environment Configuration
Uses python-decouple for environment variables:
- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (bool)
- `ALLOWED_HOSTS`: Comma-separated hosts
- `EMAIL_HOST_USER`: SMTP email address
- `EMAIL_HOST_PASSWORD`: SMTP password

Create `.env` file based on `.env.example`

## Development Notes

### Testing
- Tests use Django's TestCase framework
- pytest is installed but pytest-django is not configured
- Use `python manage.py test` for running tests

### Logging
Configured for apps: league, users, content
- Logs to both console and `debug.log` file
- Level: DEBUG for league app, INFO for users/content

### Database
- Development: SQLite (db.sqlite3)
- Custom managers and efficient querysets with select_related/prefetch_related used throughout

### Static/Media Files
- STATIC_URL: '/static/'
- STATIC_ROOT: staticfiles/
- MEDIA_URL: '/media/'
- MEDIA_ROOT: media/

### Signal Interdependencies
**Important**: Users and League apps have circular imports via signals
- users.models imports league.Player and league.Coach
- users.signals creates Player/Coach based on user role
- Handle with care when modifying models or signals
