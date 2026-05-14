# Admin And Score Migration Design

## Goal

Migrate the existing Flask template-based management and score-entry pages to Vue while keeping the current Flask + Vue architecture, preserving existing business behavior, and keeping old template routes available as a rollback path during the first migration stage.

## Current Context

The project currently has a Vue 3 + Vite frontend for the big-screen display and a Flask backend that still owns several operational HTML pages:

- `/`: upload registration Excel and show team data.
- `/create_table`: show team score/ranking data and control current round/timer.
- `/generate_matches`: view and regenerate match pairings.
- `/modify_select_table`: admin entry for modifying scores by round and table.
- `/select_table`: score-entry table lookup using the current round.
- `/input_scores/<table>/<turn>/<type>`: score-entry form.

The backend already exposes display-oriented JSON endpoints, especially `/dashboard_snapshot`, but management actions are still coupled to form posts, redirects, and Flask flash messages in `run.py`.

## Chosen Approach

Use a phased migration:

1. Add reusable backend helper functions for the existing management workflows.
2. Add JSON APIs under `/api/admin/*` and `/api/score/*`.
3. Add Vue Router and move the current big-screen UI to `/screen`.
4. Add Vue pages for `/admin`, `/score`, and `/score/:turn/:table`.
5. Keep the old Flask template routes for the first version as a fallback.

This keeps risk moderate. The Vue pages get clean API contracts, while the old pages can still be used if a live-event workflow needs a quick rollback.

## Route Design

Frontend routes:

- `/`: redirect to `/screen` so the current default big-screen access remains convenient.
- `/screen`: current big-screen display.
- `/admin`: administrator console for registration import, round/timer control, match generation, team preview, and admin score correction.
- `/score`: score-entry landing page for users who scan a QR code. First version has no login or identity verification.
- `/score/:turn/:table`: score-entry form for one round and table.

Backend template routes:

- Keep existing template routes during the first migration.
- Update them only where needed to call shared helper functions.
- Do not remove templates or routes in this phase.

## Backend API Design

Create `GuanDan_backend-V2.0/api/admin_api.py`.

Endpoints:

- `GET /api/admin/overview`
  - Returns current round, timer text, team rows, whether matches exist, and snapshot metadata if available.
- `POST /api/admin/import`
  - Accepts one `.xlsx` file.
  - Reuses `import_registration_excel`.
  - On success clears match cache, resets current turn, and marks the dashboard snapshot stale.
- `POST /api/admin/clear`
  - Reuses `clear_all_tables`.
  - Clears match cache, resets current turn, and marks the dashboard snapshot stale.
- `POST /api/admin/turn`
  - Accepts `turn` as `1`, `2`, `3`, or `null`.
  - Updates the current round and marks the dashboard snapshot stale.
- `POST /api/admin/timer/start`
  - Starts the round timer.
- `POST /api/admin/timer/stop`
  - Stops the round timer.
- `GET /api/admin/matches`
  - Returns all match rows from `fight_info`.
- `POST /api/admin/matches/generate`
  - Generates and replaces three rounds of matches.
  - Clears match cache and marks the dashboard snapshot stale.
- `GET /api/admin/score-match?turn=<turn>&table=<table>`
  - Validates a specific round/table and returns the two teams and members.
- `POST /api/admin/scores`
  - Submits or modifies a score for an explicit round/table.

Create `GuanDan_backend-V2.0/api/score_api.py`.

Endpoints:

- `GET /api/score/current-turn`
  - Returns the current round for the score landing page.
- `GET /api/score/table?table=<table>`
  - Uses the current round and requested table to return the two teams and members.
- `POST /api/score/table`
  - Uses the current round and requested table to submit the score.

Response format:

```json
{
  "ok": true,
  "message": "operation succeeded",
  "data": {}
}
```

Failure format:

```json
{
  "ok": false,
  "message": "current turn is not set",
  "error": "invalid_turn"
}
```

The actual user-facing `message` value may be localized in Chinese. The API contract depends on the stable `ok` boolean and `error` code.

## Backend Helper Design

Add a small service layer instead of copying logic into new APIs:

- Import workflow helper:
  - Validate file presence, extension, and secure filename.
  - Save upload.
  - Run import.
  - Clear match cache, reset current round, mark snapshot stale.
- Match generation helper:
  - Fetch match source data.
  - Generate three rounds.
  - Replace `fight_info`.
  - Clear match cache and mark snapshot stale.
- Match lookup helper:
  - Validate round and table.
  - Load fight info.
  - Return team names and members.
- Score submission helper:
  - Load match info.
  - Build score update.
  - Use Redis writeback queue when enabled, otherwise write directly to MySQL.
  - Mark snapshot stale.
  - Save score log.

The existing HTML routes should call these helpers after they exist. That avoids diverging behavior between the Vue pages and old Flask pages.

## Frontend Design

Add `vue-router`.

Files:

- `GuanDanFront-V2.0/src/router/index.js`
  - Defines `/`, `/screen`, `/admin`, `/score`, and `/score/:turn/:table`.
- `GuanDanFront-V2.0/src/views/ScreenView.vue`
  - Receives the existing big-screen logic from `App.vue`.
- `GuanDanFront-V2.0/src/views/AdminView.vue`
  - Main admin console shell.
- `GuanDanFront-V2.0/src/views/ScoreEntryView.vue`
  - Current round display and table-number entry.
- `GuanDanFront-V2.0/src/views/ScoreFormView.vue`
  - Team display and score submission form.
- `GuanDanFront-V2.0/src/api/admin.js`
  - Admin API wrapper.
- `GuanDanFront-V2.0/src/api/score.js`
  - Score-entry API wrapper.
- `GuanDanFront-V2.0/src/components/admin/*`
  - Focused admin sections if `AdminView.vue` becomes too large.

Admin page sections:

- Event initialization:
  - Upload Excel.
  - Clear business data with confirmation.
  - Preview imported team rows.
- Round and timer control:
  - Show current round and timer text.
  - Set round to `1`, `2`, `3`, or unset.
  - Start and stop timer.
- Match management:
  - Show all match rows.
  - Regenerate matches with confirmation.
- Score correction:
  - Input round and table.
  - Reuse the same score form behavior as `/score/:turn/:table`.
- Screen status:
  - Show snapshot update time if available.
  - Link to `/screen`.

Score page behavior:

- `/score` loads current round.
- If no valid round exists, show a clear message and disable table lookup.
- If a round exists, user enters table number and navigates to `/score/<turn>/<table>`.
- `/score/:turn/:table` loads match info, shows both teams and members, then submits score.
- If both teams have the same final level, the user must choose the last-game winner.
- QR login, identity, and permissions are intentionally out of scope for this first migration.

## Error Handling

Backend:

- Return consistent `ok/message/error/data` JSON.
- Use stable error codes:
  - `invalid_turn`
  - `invalid_table`
  - `match_not_found`
  - `invalid_file`
  - `import_failed`
  - `match_generation_failed`
  - `score_invalid`
  - `winner_required_when_tied`
  - `score_write_failed`
- Keep dangerous operations explicit and narrow.

Frontend:

- Render errors inline instead of relying on `alert`.
- Use confirmation dialogs for clearing all business data and regenerating matches.
- Keep `/score` focused and readable on mobile because QR scans will route users there in a future authentication phase.
- Show whether a score update was queued or written directly.

## Testing And Verification

Backend tests:

- Add tests for score parsing and score submission helper behavior where database access can be mocked.
- Add API tests with Flask test client where practical.
- Cover:
  - No current round returns `invalid_turn`.
  - Invalid or missing table returns `invalid_table` or `match_not_found`.
  - Same final level without winner returns `winner_required_when_tied`.
  - Successful score submission marks the snapshot stale.
  - Admin match generation returns a clear failure if the algorithm cannot generate matches.

Run:

```powershell
cd GuanDan_backend-V2.0
python -m unittest discover -s tests -p "test_*.py" -v
```

Frontend verification:

```powershell
cd GuanDanFront-V2.0
npm run build
```

Manual verification:

- `/screen` still renders the big-screen display.
- `/admin` can import data, set round, control timer, generate matches, and enter admin score correction.
- `/score` can load current round, accept a table number, and submit a score.
- After a data-changing action, the big screen refreshes on the next polling cycle.

## Git Strategy

Use small commits:

1. `docs: add admin migration design`
2. `feat: add admin and score json APIs`
3. `feat: route frontend screen admin score pages`

If the frontend route migration is large, split the third commit into:

- `feat: move screen display behind vue router`
- `feat: add admin and score vue pages`

Only stage files that belong to the current step. The repository already contains unrelated local changes and generated files, so commits must avoid broad `git add .`.

## Out Of Scope

- User login for QR score entry.
- Fine-grained permissions.
- Removing old Flask templates.
- Visual polish beyond functional Vue pages.
- Replacing Flask, Vue, MySQL, or Redis.
- Bulk deletion of files or directories.
