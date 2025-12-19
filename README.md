# League & Fantasy Sports Manager

A comprehensive Django web application for managing sports leagues, including real-time features, fantasy leagues, and role-based user dashboards.

## 🚀 Features

### League Management
- **Core Entities:** Manage Teams, Players, Coaches, and Matches.
- **Match Management:** Schedule matches, track live scores, and record match events (goals, cards, substitutions).
- **Standings:** Automatic calculation of league standings based on points, goal difference, and goals scored.
- **Lineups:** Interactive, mobile-friendly lineup manager for coaches to set starting 11 and substitutes.
- **Statistics:** Detailed player and team statistics per season.

### Fantasy League
- **Fantasy Teams:** Users can create fantasy teams with budget caps.
- **Transfers:** Buy and sell players within a budget.
- **Scoring:** Automated point calculations based on real-match performance.
- **Leaderboards:** Weekly and overall fantasy rankings.

### User System
- **Role-Based Access:** Specialized dashboards for Admins, Coaches, Players, and Fans.
- **Authentication:** Email-based login and Google OAuth integration (via `django-allauth`).
- **Profiles:** User profiles linked to Player/Coach entities.

### Technical Highlights
- **Real-time Updates:** Built with Django Channels for real-time notifications.
- **Modern UI:** Styled with Tailwind CSS for a responsive and professional look.
- **Cloud Storage:** Integration with Cloudinary for media file hosting.
- **Deployment Ready:** Configured for deployment on Render.com with PostgreSQL.

## 🛠 Tech Stack

- **Backend:** Python 3.12+, Django 5.2
- **Database:** SQLite (Development), PostgreSQL (Production)
- **Frontend:** HTML5, Tailwind CSS, JavaScript
- **Real-time:** Django Channels, Redis (Production)
- **Authentication:** django-allauth
- **Storage:** Cloudinary
- **Hosting:** Render.com

## 📋 Prerequisites

- Python 3.10 or higher
- Node.js & npm (for Tailwind CSS)
- Git

## ⚡ Installation & Local Development

1.  **Clone the repository**
    ```bash
    git clone <repository-url>
    cd league_app
    ```

2.  **Create and activate a virtual environment**
    ```bash
    # Windows
    python -m venv myvenv
    .\myvenv\Scripts\Activate.ps1

    # macOS/Linux
    python3 -m venv myvenv
    source myvenv/bin/activate
    ```

3.  **Install Python dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Node.js dependencies (for Tailwind)**
    ```bash
    # Navigate to the theme app (or wherever package.json is located, usually root or theme folder)
    # Based on project structure, it seems to be in the root or handled via django-tailwind
    python manage.py tailwind install
    ```

5.  **Set up Environment Variables**
    Create a `.env` file in the project root (copy from `.env.example` if available) and add the following:
    ```env
    DEBUG=True
    SECRET_KEY=your-secret-key-here
    ALLOWED_HOSTS=localhost,127.0.0.1
    # Add other keys as needed (DB, Cloudinary, Google OAuth)
    ```

6.  **Apply Database Migrations**
    ```bash
    python manage.py migrate
    ```

7.  **Create a Superuser**
    ```bash
    python manage.py createsuperuser
    ```

8.  **Build Tailwind CSS**
    ```bash
    python manage.py tailwind build
    ```

## 🏃 Running the Application

You need to run two processes: the Django development server and the Tailwind CSS watcher.

**Terminal 1: Django Server**
```bash
python manage.py runserver
```

**Terminal 2: Tailwind Watcher** (keeps CSS in sync)
```bash
python manage.py tailwind start
```

Access the application at `http://127.0.0.1:8000/`.

## 📂 Project Structure

- `league_app/`: Main project configuration (settings, URLs, ASGI/WSGI).
- `league/`: Core league logic (Teams, Matches, Players).
- `users/`: Custom user model, authentication, and dashboards.
- `fantasy/`: Fantasy league functionality.
- `content/`: Content management and team invitations.
- `theme/`: Tailwind CSS configuration.
- `templates/`: Global HTML templates.
- `static/`: Static assets (CSS, JS, Images).

## 🌍 Deployment

This project is configured for deployment on **Render.com**.

1.  **Infrastructure as Code:** The `render.yaml` file defines the web service and PostgreSQL database.
2.  **Static Files:** Served via `Whitenoise`.
3.  **Media Files:** Stored on Cloudinary (requires `CLOUDINARY_URL` env var).
4.  **Database:** Uses `dj_database_url` to parse the `DATABASE_URL` provided by Render.

See `render_deployment_plan.md` for a detailed deployment guide.

## 🧪 Testing

Run the test suite using Django's test runner:

```bash
python manage.py test
```

## 📄 License

[MIT License](LICENSE)
