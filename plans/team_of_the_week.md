# Team of the Week Feature Implementation Plan

This document outlines the systematic plan to implement the "Team of the Week" feature, focusing on manual admin selection, a robust data model, and high-performance queries.

### **Phase 1: Backend Refinements (The Foundation)**

1.  **Bulletproof Database Models (`league/models.py`):**
    *   **`TeamOfTheWeek` Model:**
        *   `league`: A `ForeignKey` to the existing `League` model to represent a unique season (e.g., "Fall 2025").
        *   `week_number`: An `IntegerField`.
        *   `players`: A `ManyToManyField` to the `Player` model, using `TeamOfTheWeekPlayer` as the intermediary table.
        *   **Meta Option:** Add `unique_together = ('league', 'week_number')` to the model's `Meta` class to prevent duplicate entries for the same league and week.
    *   **`TeamOfTheWeekPlayer` Model:**
        *   This model will connect `TeamOfTheWeek` and `Player`.
        *   `position`: Implement a `Position` class that inherits from `models.TextChoices` (e.g., `GOALKEEPER = 'GK', 'Goalkeeper'`) to enforce data integrity and provide a validated dropdown in the admin panel.

2.  **Streamlined Admin Management (`league/admin.py`):**
    *   Create a `TeamOfTheWeekPlayerInline` using `admin.TabularInline` to allow adding, removing, and setting positions for all players directly on the `TeamOfTheWeek` admin page.
    *   Register the `TeamOfTheWeek` model with a custom `TeamOfTheWeekAdmin` class that uses this inline functionality for a seamless management workflow.

### **Phase 2: Frontend & Performance (The "Efficient" Part)**

1.  **High-Performance View Logic (`league/views.py`):**
    *   Modify the `home` view to be the intelligent engine for this feature.
    *   **Logically "Latest" Team:** For the default homepage display, fetch the team by explicitly ordering by season and week: `TeamOfTheWeek.objects.order_by('-league__year', '-week_number').first()`.
    *   **Crash-Proof Searching:** Wrap the database lookup in a `try...except TeamOfTheWeek.DoesNotExist` block. If no team is found for a selected week, the view will pass `None` to the template instead of crashing.
    *   **Eliminate N+1 Queries:** Use `prefetch_related('players')` when querying for the `TeamOfTheWeek` to fetch the team and all its associated players in a minimal number of database queries, ensuring the page loads instantly.

2.  **Dynamic & Graceful Frontend (`league/templates/`):**
    *   **Reusable Pitch Component (`partials/team_of_the_week.html`):**
        *   Create this new partial to render the pitch and players. It will be designed to gracefully handle receiving a `TeamOfTheWeek` object or `None`.
    *   **Homepage Integration (`home.html`):**
        *   Add a new section to the homepage containing a search form (with dropdowns for `League` and `Week Number`).
        *   Use an `{% if team_of_the_week %}` block to either display the pitch layout or a user-friendly message like, "The Team of the Week for this week has not been selected yet."
