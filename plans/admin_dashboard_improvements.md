# Admin Dashboard Improvement Plan

Here is a systematic, step-by-step implementation plan to transform your admin dashboard from a simple overview into a more dynamic and functional admin hub.

### Prerequisites

1.  **Code Editor:** Have your project open in your preferred code editor.
2.  **Terminal:** Keep a terminal open with your virtual environment activated to run Django's development server.
3.  **Assumptions:** This guide assumes you are using a standard Django project structure and are familiar with editing Python and HTML files.

---

### Step 1: Enhance the Backend View (`admin_dashboard_view`)

First, we'll update the view to gather more insightful data and clean up the existing code.

**File to Edit:** `users/views.py`

1.  **Import necessary models:** Add `Team` and `Count` to your imports at the top of the file.

    ```python
    from django.db.models import Count
    from league.models import Team
    ```

2.  **Modify `admin_dashboard_view`:** Replace the entire existing function with the following updated version.

    ```python
    @user_passes_test(lambda u: u.is_authenticated and u.role == 'admin')
    def admin_dashboard_view(request):
        # Key Statistics
        user_count = User.objects.count()
        player_count = Player.objects.count()
        coach_count = Coach.objects.count()
        team_count = Team.objects.count()
        active_leagues_count = League.objects.filter(is_active=True).count()
        
        # Recent Activity (e.g., latest user registrations)
        recent_users = User.objects.order_by('-created_at')[:5]

        # Season Progress
        season_progress = get_season_progress()

        # Latest Match
        latest_match = Match.objects.order_by('-date').first()

        # Admin's Profile (corrected to fetch a single object)
        profile = UserProfile.objects.get(user=request.user)

        context = {
            'profile': profile,
            'user_count': user_count,
            'player_count': player_count,
            'coach_count': coach_count,
            'team_count': team_count,
            'active_leagues_count': active_leagues_count,
            'recent_users': recent_users,
            'season_progress': season_progress,
            'latest_match': latest_match,
        }

        return render(request, 'admin_dashboard.html', context)
    ```

---

### Step 2: Update the Frontend Template

Now, let's display this new information in the dashboard template.

**File to Edit:** `users/templates/admin_dashboard.html`

This is a conceptual layout. You will need to adapt it to your existing HTML structure and CSS framework.

```html
{% extends "base.html" %}
{% load static %}

{% block content %}
<div class="container mt-4">
    <h1 class="mb-4">Admin Dashboard</h1>

    <!-- Section for Key Statistics -->
    <div class="row">
        <!-- ... (Statistic cards as provided in the previous response) ... -->
    </div>

    <!-- Section for Quick Actions and Recent Activity -->
    <div class="row mt-4">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h5>Quick Actions</h5>
                </div>
                <div class="card-body">
                    <a href="{% url 'create_user' %}" class="btn btn-primary mb-2">Create New User</a>
                    <a href="{% url 'admin:league_league_add' %}" class="btn btn-secondary mb-2">Create New League</a>
                    <a href="{% url 'admin:league_team_changelist' %}" class="btn btn-info mb-2">Manage Teams</a>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h5>Recent Registrations</h5>
                </div>
                <ul class="list-group list-group-flush">
                    {% for user in recent_users %}
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            {{ user.username }} ({{ user.get_role_display }})
                            <span class="badge badge-primary badge-pill">{{ user.created_at|timesince }} ago</span>
                        </li>
                    {% empty %}
                        <li class="list-group-item">No recent registrations.</li>
                    {% endfor %}
                </ul>
            </div>
        </div>
    </div>

</div>
{% endblock %}
```

---

### Step 3: Implement Search Functionality

This requires changes to `urls.py`, `views.py`, and creating a new template.

1.  **Add Search URL**
    *   **File:** `users/urls.py`
    *   Add: `path('admin/search/', views.admin_search_results_view, name='admin_search_results'),`

2.  **Create the Search View**
    *   **File:** `users/views.py`
    *   Add the new view function to handle the search logic.

    ```python
    # Add this view to users/views.py
    @user_passes_test(lambda u: u.is_authenticated and u.role == 'admin')
    def admin_search_results_view(request):
        query = request.GET.get('q', '')
        
        if query:
            users = User.objects.filter(
                Q(username__icontains=query) | 
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )
        else:
            users = User.objects.none()

        context = {
            'query': query,
            'users': users,
        }
        return render(request, 'admin_search_results.html', context)
    ```

3.  **Add Search Bar to Dashboard Template**
    *   **File:** `users/templates/admin_dashboard.html`
    *   Add this form at the top, below the `<h1>` title.

    ```html
    <form action="{% url 'admin_search_results' %}" method="get" class="form-inline">
        <input class="form-control mr-sm-2" type="search" placeholder="Search for users..." name="q" aria-label="Search">
        <button class="btn btn-outline-success my-2 my-sm-0" type="submit">Search</button>
    </form>
    ```

4.  **Create the Search Results Template**
    *   **Create New File:** `users/templates/admin_search_results.html`
    *   Add the following content to display the results.

    ```html
    {% extends "base.html" %}

    {% block content %}
    <div class="container mt-4">
        <h1>Search Results for "{{ query }}"</h1>

        <div class="card mt-4">
            <div class="card-header">
                Found {{ users.count }} User(s)
            </div>
            <ul class="list-group list-group-flush">
                {% for user in users %}
                    <li class="list-group-item">
                        <a href="#">{{ user.username }}</a> - {{ user.email }} (Role: {{ user.get_role_display }})
                    </li>
                {% empty %}
                    <li class="list-group-item">No users found matching your query.</li>
                {% endfor %}
            </ul>
        </div>
        
        <a href="{% url 'admin_dashboard' %}" class="btn btn-primary mt-4">Back to Dashboard</a>
    </div>
    {% endblock %}
    ```
