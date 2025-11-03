# Plan for Mobile-Friendly Lineup Manager

This document outlines the plan to make the lineup manager interface responsive and mobile-friendly.

### **Phase 1: Responsive Layout and Controls (CSS)**

The first step is to make the existing layout adapt to smaller screen sizes. This will be done primarily with CSS.

1.  **Flexible Pitch:** I will modify the CSS to make the football pitch container scale down proportionally on smaller screens. Instead of fixed pixel widths, I'll use percentage-based widths and `vw` (viewport width) units to ensure it fits within the screen.
2.  **Vertical Stacking:** The multi-column layout (Pitch, Substitutes, Available Players) will be converted into a single-column layout on mobile. The "Substitutes" and "Available Players" sections will stack vertically below the pitch, making them easy to scroll through.
3.  **Optimized Player Lists:** The "Available Players" list, which can be long, will be made collapsible to save vertical space. A "Show/Hide Available Players" button will be added.
4.  **Responsive Controls:** The "Formation" dropdown and "Save Lineup" button will be resized to be larger and more easily tappable on touchscreens. I will also ensure they are positioned accessibly.

### **Phase 2: Touch-Friendly Interactions (JavaScript)**

Drag-and-drop can be difficult on small touchscreens. This phase will introduce a more mobile-friendly way to manage the lineup.

1.  **Implement "Tap-to-Move":** I will enhance the `lineup-manager.js` file to add a "tap-to-move" interaction.
    *   **Tap a player:** When a user taps a player, that player will be highlighted as "selected."
    *   **Tap a destination:** When the user then taps an empty pitch slot or the substitute bench, the selected player will instantly move there.
    *   This provides a more precise alternative to dragging and is much easier to use on a phone. The existing drag-and-drop will remain active for desktop users.
2.  **Visual Feedback:** I will add clear visual cues for the "tap-to-move" feature. The selected player will have a distinct border, and valid destination slots will be highlighted, guiding the user through the process.

### **Phase 3: Performance and UI Polish**

Finally, I'll add some finishing touches to improve the overall experience.

1.  **Player Search:** I will add a search bar above the "Available Players" list. This will allow coaches to quickly filter the list by name, which is especially useful for teams with many players.
2.  **Lazy Loading (Optional):** If the player lists are very long and contain many images, I can implement lazy loading for the player figurines to improve initial page load time.
