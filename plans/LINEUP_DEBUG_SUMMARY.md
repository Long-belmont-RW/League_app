# Lineup Manager Debugging Summary

Date: 2025-10-27

Purpose

- Summarize all changes applied while investigating why lineup edits weren't persisting in the UI after a successful save.
- Provide reproduction evidence and logs collected during the session.
- Give a concise prompt for Gemini Pro (or any powerful code assistant) so it can run an automated analysis and propose fixes (or apply them).

---

## Quick TL;DR

- The server was successfully persisting lineup POSTs (database rows and POST response show correct, canonical data).
- The client sometimes displayed stale data after reload. To defend against that, I added a small JSON GET endpoint and a proactive frontend fetch so the client requests authoritative `js_data` from the server on init and applies it.
- Despite that, you reported the UI is still not consistently showing saved data. Likely root causes: stale browser cache / wrong static file copy being served / race conditions or a service worker / template caching. The next step is to let Gemini Pro perform an automated, repository-wide sweep for those issues and propose or apply fixes.

---

## Reproduction steps used during debugging

1. Open match lineup page: `/matches/2/lineup/`
2. Move players around, ensure exactly 11 starters, then click _Save Lineup_.
3. Observe network POST to `/matches/2/lineup/` with payload:
   - { team_id, formation, starters: [...ids], substitutes: [...ids] }
4. Inspect POST response (server returned `status: success` and `data` containing canonical `starters` and `substitutes` full objects).
5. Reload the page and inspect the injected `home-team-data` / `away-team-data` JSON scripts to verify what the server rendered on GET.
6. Look at server runserver logs (INFO messages for POST and GET) and browser Console/Network for client-side behavior.

Evidence gathered (examples from runserver & DevTools):

- Server POST log (saved):
  INFO: Lineup save attempt: user=lng, match=2, payload={'team_id': 2, ...}
  INFO: Lineup saved: lineup_id=3 match=2 team=2 starters=11 subs=1 by user=lng

- POST response JSON sample (success):
  {
  "status": "success",
  "message": "Lineup saved successfully!",
  "data": {
  "lineup_id": 3,
  "starters": [ {"id":21,...}, ... ],
  "substitutes": [ {"id":4,...} ]
  }
  }

- Injected template JSON on reload (example):

  - `document.getElementById('home-team-data').textContent` contains the server-injected `js_data` for the home team.
  - `document.getElementById('away-team-data').textContent` likewise for away.

- Server GET log after reload shows serialized starters/substitutes matching the saved data.

---

## All code changes applied during the investigation (chronological)

Note: below lists only files touched and the high-level change. See the repo for exact diffs (commits are not created here).

1. static/js/lineup-manager.js

   - Added `normalizePlayerArrays()` to ensure starters/substitutes/availablePlayers are enriched objects (not only ids).
   - Added backward-compatible alias `createPlayerCard()` -> `createPlayerFigurine()` to avoid runtime TypeError from mixed script versions.
   - Fixed `moveAllStartersToBench()` so it updates internal arrays when moving DOM nodes to the bench.
   - Introduced `applyServerState(serverData)` to accept canonical serialized players from the server and fully re-render UI/state.
   - On save success, the client now prefers `result.data` (server canonical) and calls `applyServerState()`.
   - Added proactive `fetchCanonicalState()` (called from `init()`) that GETs `?format=json&team_id=<id>` and applies server state on init.
   - Small toast improvements: added X button, subtle progress bar, and auto-hide (implementation iterations; some were reverted earlier).

2. league/views.py

   - `handle_lineup_save` (POST):
     - Added validation logging and exception logging.
     - After saving, returns serialized `starters` and `substitutes` (full player objects) inside the JSON response so frontend can apply canonical state.
   - `get_team_lineup_context`:
     - Added debug logging to print which `LineupPlayer` rows exist in DB at GET time and which ids are serialized to `starters` and `substitutes`.
   - `manage_lineup_view` (GET):
     - Added support for `GET ?format=json&team_id=<id>` returning canonical `js_data` (so the client can fetch authoritative JSON after initialization).
     - Also guarded earlier permission checks and logging.

3. static/css/lineup-styles.css

   - Spacing/visual improvements for pitch slots and figurines (not relevant to persistence but part of UX fixes).

4. Misc
   - Created a tracked todo list (internal to the debugging session) and iteratively updated it.

---

## Current state & findings

- The DB save works and server-side rendering of `js_data` matches the persisted lineup (server logs confirm serialized starters/subs and `get_team_lineup_context` logs show canonical rows).
- The frontend now fetches canonical JSON on init and applies it. That should eliminate stale-injection problems.
- Despite all of the above, you reported the UI still appears to show stale data after reload. The likely remaining causes are:
  - The browser is still loading an older copy of `lineup-manager.js` (or another stale static asset). There are two copies in the repo (`static/js/lineup-manager.js` and `staticfiles/js/lineup-manager.js`) — potential divergence.
  - A service worker, proxy, CDN, or webserver caching layer is serving an old JS bundle.
  - The template is referencing a different static path than the one modified in repo, or `collectstatic`/static gathering step isn't run in deployment.
  - A race between two LineupManager instances (home and away) or duplicate IDs in DOM/initialization could cause unexpected rendering.

---

## Suggested high-value checks (manual) before automated changes

1. Hard-reload and confirm network:
   - In browser DevTools -> Network, enable "Disable cache" and reload the page.
   - Verify the `lineup-manager.js` request (check the actual file contents in Response tab) — confirm it contains the new `fetchCanonicalState()` and `applyServerState()` code (search for `fetchCanonicalState` or `applyServerState`).
2. Check for duplicate static copies:
   - Search the repo for other copies of `lineup-manager.js` and any references to `staticfiles/js/lineup-manager.js` in templates.
3. Check service worker / caching layers:
   - Look for `service-worker.js` or references in templates.
   - If using Django runserver, caching is less likely, but browser caching or devtools cache can interfere.
4. Confirm injected JSON on reload:
   - In Console run:
     - `document.getElementById('home-team-data').textContent`
     - `document.getElementById('away-team-data').textContent`
   - Confirm ids match saved POST response.
5. Confirm the client applied server state after save (no client-side errors):
   - After the POST, check Console for `LineupManager: applying canonical server state` debug output.

---

## Recommended automatic / patch fixes for Gemini Pro to consider/apply

1. Ensure the page response disables caching (quick protection): modify `manage_lineup_view` POST/GET render return like:

```python
response = render(request, 'lineup_manager.html', context)
response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
return response
```

2. Force versioning on the static JS include in template (temporary):

```django
<script src="{% static 'js/lineup-manager.js' %}?v={{ now|date:"U" }}"></script>
```

or better, inject a project STATIC_VERSION from settings and use that.

3. Remove or reconcile duplicate static copies:

   - Find `staticfiles/js/lineup-manager.js` and either remove it or ensure `collectstatic` is run and the served asset is the canonical one.

4. Add server-side endpoint test and small UI test:

   - Unit test asserting POST and subsequent GET return the same serialized starters/subs.

5. Add logging to the frontend `fetchCanonicalState()` success path if not present (already added) and also add a console.error if `applyServerState` throws (so we can capture the reason why client didn't update).

---

## Exact GitHub/Gemini Pro prompt (copy/paste)

Below is a ready-made prompt for a capable assistant (Gemini Pro). It contains everything needed to analyze the repository, reproduce the issue, and either propose or apply fixes.

--- PROMPT START ---
Repository: League_app (branch: main)
Project root: c:\Users\USER\Documents\Projects\Django\League App\League_app
Primary goal: the lineup manager's client UI sometimes does not show the lineup that has been successfully saved to the server. The server saves successfully (POST returns canonical serialized players), but after page reload the UI can still display stale lineup data. Fix root cause(s) and make client/server behavior robust.

Key facts & findings already known (do not repeat probing work unless needed):

- Backend `manage_lineup_view` accepts POST and writes Lineup / LineupPlayer rows. After save it returns JSON with `data.starters` and `data.substitutes` (full player objects).
- `get_team_lineup_context()` builds `js_data` and injects it into the template inside `home-team-data` and `away-team-data` JSON script tags.
- I added a GET handler on `manage_lineup_view` for `?format=json&team_id=<id>` that returns canonical `js_data`.
- The frontend `static/js/lineup-manager.js` now has `applyServerState()` and `fetchCanonicalState()` that requests `?format=json&team_id=` on init and applies the payload.
- Server logs indicate POST succeeded and GET injection contains the canonical players. Yet the UI still occasionally shows stale data on reload.

Task for Gemini Pro:

1. Run a repository-wide static analysis/search for caching/static duplication issues:

   - Find all copies of `lineup-manager.js` and all template references to it.
   - Identify whether templates reference `staticfiles/js/lineup-manager.js` or another path.
   - Identify any service worker, caching middleware, or proxies that could cause stale JS to be served.

2. Reproduce the issue locally (instructions):

   - Start Django dev server: `python manage.py runserver`.
   - Open DevTools -> Network (disable cache) -> open `/matches/2/lineup/`.
   - Perform a save and reload, inspect Network/Console to verify which `lineup-manager.js` file was fetched and whether `fetchCanonicalState()` executed.

3. If stale JS/static is the issue, apply one of the following fixes and test:

   - Ensure templates reference the correct canonical static path (single source). Remove or consolidate duplicate static copies.
   - Add cache-busting/asset versioning to `lineup-manager.js` include (temporary or via settings.STATIC_VERSION).
   - Optionally add `Cache-Control: no-store` to the `manage_lineup_view` response while debugging/short-term.

4. If static files are confirmed correct, but the client still doesn't apply server state, instrument the client further:

   - Add console.error catches around `applyServerState()` and log stack traces and incoming payload sizes.
   - Ensure `applyServerState()` is idempotent and not blocked by other code (e.g., not overridden by a duplicate instance or race).

5. Optionally add a tiny integration test:
   - Django test that POSTs a lineup, then GETs the lineup page and asserts `home_team_context.js_data['starters']` equals the JSON returned from POST. This verifies server-end consistency.

Deliverables (apply or propose changes):

- A patch that removes duplicate static assets or adjusts template include to canonical asset and adds versioning.
- Optionally, add `Cache-Control: no-store` on `manage_lineup_view` for troubleshooting.
- Console/DevTools evidence that `fetchCanonicalState()` executes and `applyServerState()` runs without errors.
- A short report summarizing root cause and applied changes.

Constraints & safety:

- Keep changes small and reversible in this sprint.
- Prefer configuration (cache headers, versioning) over removing large asset directories until team confirms.

--- PROMPT END ---

---

If you'd like, I can also apply one or two of the recommended patches right away (for example: add `Cache-Control` to the view response, or add versioning param to the template include). Tell me which patch to apply, or forward the Gemini Pro prompt to your code-assistant to run automatically.

---

Appendix: Files of interest (quick list)

- `static/js/lineup-manager.js` (client)
- `staticfiles/js/lineup-manager.js` (older/duplicate copy) — verify and reconcile
- `league/views.py` (manage_lineup_view, handle_lineup_save, get_team_lineup_context)
- `league/templates/lineup_manager.html` (includes `home-team-data` and `away-team-data` JSON injections and script include)

---

If you want, I will also (A) add the `Cache-Control` header to the view now, or (B) add a version query param to the template JS include — tell me which and I will patch immediately.
