# Plan: Mobile-Friendly Lineup Manager

This document outlines the work done and the remaining steps to make the Lineup Manager feature mobile-friendly.

## Goal

The objective is to refactor the `lineup_manager.html` page to provide an intuitive and usable experience on mobile devices, while retaining the existing functionality for desktop users.

## Work Completed

The initial phase focused on restructuring the HTML templates to support an adaptive layout.

### 1. Tabbed Interface for Mobile
- **File Modified:** `league/templates/lineup_manager.html`
- **Changes:**
    - A tabbed navigation structure (Home Team / Away Team) was added.
    - This tab bar is only visible on screens smaller than the `xl` breakpoint (mobile and tablet).
    - On `xl` screens and larger, the original two-column grid layout is preserved.
    - Basic JavaScript for handling tab switching was added directly to the template's `<script>` block.

### 2. Team Panel Restructuring
- **File Modified:** `league/templates/partials/lineup_team_panel.html`
- **Changes:**
    - **Collapsible Sections:** The "Substitutes Bench" and "Available Players" areas were wrapped in an accordion structure to make them collapsible.
    - **Mobile Modal:** The HTML for a modal was added. On mobile, the "Available Players" list is intended to be moved into this modal to save screen space.
    - **Roster Button:** A "Manage Roster" button was added, which is visible only on mobile and is intended to trigger the player modal.
    - **Search Bar:** An `<input type="search">` was added to the "Available Players" section (for both desktop view and the mobile modal) to allow for player filtering.

## Next Steps (Work In Progress)

The next phase involves implementing the client-side logic in JavaScript to power the new UI components and adapt the user interaction model for touchscreens.

- **File to be Modified:** `static/js/lineup-manager.js`

### Required JavaScript Implementation:

1.  **Activate Collapsible Sections:** Add event listeners to the accordion triggers to toggle the visibility of the content panels.
2.  **Implement Modal Logic:**
    - Write functions to open and close the "Available Players" modal on mobile.
    - Ensure the player list is correctly populated or cloned into the modal when opened.
3.  **Implement Player Search:** Add an `onkeyup` or `oninput` event listener to the search bar to filter the list of available players in real-time.
4.  **Create a "Tap-to-Move" Interaction for Mobile:**
    - Detect the screen size upon initialization.
    - If on a small screen (e.g., `< 1280px`), **do not** initialize the `Sortable.js` drag-and-drop library.
    - Instead, implement a tap-based system:
        - Tapping a player in any list gives them a "selected" state.
        - Tapping a destination (e.g., the "Starters" pitch area or the "Substitutes" bench) moves the selected player there.
        - Tapping a second player could initiate a swap.

**Current Status:**
Progress is currently paused at this point, pending the implementation of the JavaScript logic described above.