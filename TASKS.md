# TASKS — Auth, DB-backed tracker, and dark-theme toggle

Branch: `feature/auth-and-tracker-db` (off `feature/design`).
Target PR base: `feature/design`.

This file slices the work into four epics and concrete stories. Each story is sized so a junior dev can take it independently, in roughly the listed order. Stories ship as their own commit.

## Context

- Stack: Flask 3 + gunicorn (`api/app.py`), single SQLite file at `out/jobhubmine.db`, React 18 CRA SPA (`web/`), nginx proxies `/api/*` → Flask. WAL mode enabled at first connect.
- `feature/design` already has the kit shell merged. The SPA today gates the app on a localStorage flag (`jh_authed`) and stores tracked jobs in `localStorage.jh_jobs`. We are replacing both with API-backed equivalents.
- All commands run inside Docker (no host installs). `docker compose build api web` + `docker compose up -d` after changes.
- Conventional commits, no co-author lines.

## Glossary

- **Tracker / tracked job**: a job a logged-in user has hearted from search. Carries stage (`salva`/`aplicada`/…), notes, and an event history. Today this lives in localStorage; we are moving it to the DB.
- **Session**: Flask's signed-cookie session (`flask.session`). HttpOnly, Lax SameSite, signed with `SECRET_KEY` from env. No new auth library needed.

---

## Epic 1 — Auth backend (Flask + SQLite)

Goal: users can register, log in, log out, and the API can identify the current user from a cookie. No new Python dependencies — `werkzeug.security` ships with Flask.

### Story 1.1 — Add `users` table + per-worker schema migration

**Why**: we need somewhere to put accounts. Mirror the existing `_DETAIL_MIGRATIONS` pattern (`api/app.py:34-79`) so the table appears on first API start without manual SQL.

**Files**

- `sqlite-init.sql` — append a `CREATE TABLE IF NOT EXISTS users (...)` block at the end (before any `COMMIT`). Columns: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `username TEXT NOT NULL UNIQUE COLLATE NOCASE`, `password_hash TEXT NOT NULL`, `created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))`. Add `CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)`.
- `api/app.py` — add an `_ensure_users_schema()` function modeled on `_ensure_detail_schema()` (lines 47-76). Call it at module import next to the existing call (line 79). It should `CREATE TABLE IF NOT EXISTS users (...)` so the API works even if `sqlite-init.sql` hasn't been re-applied.

**Definition of done**

- After `docker compose up -d`, `sqlite3 out/jobhubmine.db ".schema users"` shows the table.
- Restarting the API a second time logs nothing about creating the table (idempotent).

**Estimate**: 1h.

### Story 1.2 — Password hashing helpers

**Why**: never store raw passwords. Centralize hashing so endpoints don't reach into werkzeug directly.

**Files**

- `api/auth.py` (new) — three functions: `hash_password(plain: str) -> str`, `verify_password(plain: str, hashed: str) -> bool`, `is_valid_password(plain: str) -> tuple[bool, str | None]` (min 8 chars, must contain a non-whitespace, return reason on failure).
- Use `werkzeug.security.generate_password_hash` (default scrypt) and `check_password_hash`.

**Definition of done**

- `hash_password('hunter2')` returns a string starting with `scrypt:`.
- `verify_password('hunter2', hash_password('hunter2'))` is `True`.
- `is_valid_password('short')` returns `(False, 'Senha precisa ter ao menos 8 caracteres')`.

**Estimate**: 30 min.

### Story 1.3 — Auth endpoints (register/login/logout/me)

**Why**: the SPA needs HTTP routes to drive the auth flow.

**Files**

- `api/app.py` — add a Flask blueprint or just bare routes:
  - `POST /api/auth/register` — body `{username, password}`. Validate with `is_valid_password`. `INSERT` into `users`. On `IntegrityError` (duplicate username) return 409. On success return `{user: {id, username}}` and call `_login_session(user_id)`.
  - `POST /api/auth/login` — body `{username, password}`. SELECT by username, `verify_password`. On match call `_login_session(user_id)` and return `{user: {id, username}}`. On miss return 401 with a generic message (no enumeration).
  - `POST /api/auth/logout` — clears `session.pop('user_id', None)`. Return 204.
  - `GET /api/auth/me` — returns the current user (200) or 401 if no session.
- `api/app.py` — `_login_session(user_id)` sets `session['user_id'] = user_id` and `session.permanent = True`.
- `api/app.py` — at app boot, set:
  - `app.secret_key = os.environ['SECRET_KEY']` (raise if missing in non-debug)
  - `app.config['SESSION_COOKIE_HTTPONLY'] = True`
  - `app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'`
  - `app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE','false').lower() == 'true'` (default off for local dev over http)
  - `app.permanent_session_lifetime = timedelta(days=30)`
- `.env_sample` — add `SECRET_KEY=change-me-in-prod` and `SESSION_COOKIE_SECURE=false`.
- `docker-compose.yml` — pass `SECRET_KEY` and `SESSION_COOKIE_SECURE` env to the `api` service (existing pattern: copy how `JOBHUBMINE_DATABASE` is wired).

**Definition of done**

- `curl -c c.txt -X POST -H 'Content-Type: application/json' -d '{"username":"a","password":"hunter22"}' http://localhost:8080/api/auth/register` returns 200 with `{"user":{"id":1,"username":"a"}}` and writes a `session` cookie.
- `curl -b c.txt http://localhost:8080/api/auth/me` returns the user.
- `curl -b c.txt -X POST http://localhost:8080/api/auth/logout` returns 204 and the next `me` returns 401.
- Re-running register with the same username returns 409.
- Wrong-password login returns 401 with the same body shape as wrong-username login (no enumeration).

**Estimate**: 3h.

### Story 1.4 — `@login_required` decorator and `current_user_id()` helper

**Why**: subsequent epics will need a one-liner to protect routes.

**Files**

- `api/auth.py` — `def current_user_id() -> int | None: return flask.session.get('user_id')`.
- `api/auth.py` — `@login_required` decorator: returns `(jsonify({'error':'auth required'}), 401)` if `current_user_id()` is None, else proxies to the wrapped function. Use `functools.wraps`.

**Definition of done**

- A throwaway protected route (e.g. `GET /api/auth/me` already in 1.3) uses the decorator and returns 401 without a session, 200 with one.
- Add a smoke test in the PR description: `curl /api/jobs` (still public) vs. a route using `@login_required`.

**Estimate**: 30 min.

### Story 1.5 — Documentation

**Why**: the next dev (or future-you) shouldn't have to read source.

**Files**

- `CLAUDE.md` — under "API Endpoints" add the four `/api/auth/*` routes. Add a brief "Auth model" subsection: cookie session, `SECRET_KEY` required, no Flask-Login, password via `werkzeug.security.generate_password_hash`.
- `README.md` — one-line "Set `SECRET_KEY` in `.env` before running".

**Definition of done**: PR diff includes the doc updates; CLAUDE.md table reads correctly.

**Estimate**: 30 min.

---

## Epic 2 — Auth frontend

Goal: the SPA replaces the localStorage gate (`Login.jsx` writing `jh_authed`) with the real API. Same UX shape — same modal, same flow — just talking to the backend.

### Story 2.1 — Auth API client + `useAuth` hook

**Files**

- `web/src/utils/api.js` (new) — a thin `fetchJSON(path, opts)` that prepends `API_URL`, sets `credentials: 'include'` (cookies cross the proxy), throws an `Error` with `{status, body}` on non-2xx. Replaces ad-hoc `fetch(`${API_URL}/...`)` calls over time but the only required first user is auth.
- `web/src/hooks/useAuth.js` (new) — exposes `{user, status, register, login, logout, refresh}`. `status` ∈ `{'loading','anonymous','authenticated'}`. On mount calls `/api/auth/me`. `login`/`register` POST then refresh. `logout` POSTs then clears state.
- Keep `web/src/hooks/useUser.js` for cosmetic preferences (theme; see Epic 4) but **stop using it for identity** — identity comes from `useAuth`.

**Definition of done**

- Open the SPA: `useAuth` calls `/api/auth/me` once on mount; if the user has a session the dashboard renders directly without re-login.
- `console` shows no more reads of `jh_authed` from localStorage.

**Estimate**: 2h.

### Story 2.2 — Replace `Login.jsx` with a real login + register form

**Files**

- `web/src/components/Login.jsx` — replace the name-only form with `username` + `password` inputs and a "Criar conta" toggle that switches the submit between login and register. Show inline errors from `useAuth`.
- `web/src/App.js` — replace `useState(authed)` and the `localStorage.getItem('jh_authed')` lazy init with `const { user, status } = useAuth();`. Render `<Login />` when `status !== 'authenticated'`. Drop `handleEnter`.

**Definition of done**

- A wrong password shows "Usuário ou senha inválidos" (the API's generic 401 body).
- Register-with-existing-username shows "Esse usuário já existe" (translate the 409 body).
- After a successful login, refreshing the page lands on the dashboard without re-login.

**Estimate**: 3h.

### Story 2.3 — Logout button in the user menu calls the API

**Files**

- `web/src/App.js` — `handleLogout` calls `useAuth().logout()` instead of touching localStorage. Drop the `localStorage.removeItem('jh_authed')` line and the `setUser({...})` reset; both are managed by `useAuth`.
- `web/src/components/Sidebar.jsx` — no changes; the foot menu's "Sair" already calls `onLogout`.

**Definition of done**: clicking Sair returns the user to the Login screen, and `/api/auth/me` returns 401 afterwards.

**Estimate**: 30 min.

---

## Epic 3 — Tracker persisted in DB per user

Goal: replace `useTrackedJobs` (localStorage) with API-backed equivalents. Same hook shape, same callsites — minimal churn for the kit pages we just shipped.

### Story 3.1 — `tracked_jobs` table + migration

**Why**: this is the table that holds Saved/Pipeline rows.

**Files**

- `sqlite-init.sql` — append:
  ```sql
  CREATE TABLE IF NOT EXISTS tracked_jobs (
      user_id     INTEGER NOT NULL,
      job_id      TEXT NOT NULL,
      source      TEXT NOT NULL,
      title       TEXT NOT NULL,
      company_name TEXT,
      company_id  TEXT,
      location    TEXT,
      job_url     TEXT,
      job_type    TEXT,
      job_department TEXT,
      workplace_type TEXT,
      workplace_city TEXT,
      workplace_state TEXT,
      stage       TEXT NOT NULL DEFAULT 'salva',
      notes       TEXT NOT NULL DEFAULT '',
      events      TEXT NOT NULL DEFAULT '[]',  -- JSON array
      created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      PRIMARY KEY (user_id, job_id),
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
  );
  CREATE INDEX IF NOT EXISTS idx_tracked_user ON tracked_jobs(user_id);
  CREATE INDEX IF NOT EXISTS idx_tracked_user_stage ON tracked_jobs(user_id, stage);
  ```
- `api/app.py` — extend `_ensure_users_schema` (or rename to `_ensure_app_schema`) to also create `tracked_jobs` if missing.

**Definition of done**

- `.schema tracked_jobs` shows the table with the FK and indexes.
- Inserting two rows with the same `(user_id, job_id)` raises `UNIQUE constraint failed`.

**Estimate**: 1h.

### Story 3.2 — Tracker CRUD endpoints

**Files**

- `api/app.py`:
  - `GET /api/me/tracked` (`@login_required`) — returns `{tracked: [...]}`. Each row deserializes `events` from JSON.
  - `POST /api/me/tracked` — body is the snapshot built by `jobRowToTracked` (web/src/App.js:20-35). Validate `job_id` and `source` non-empty. `INSERT OR IGNORE` (no error if already saved). `events` defaults to `[{when: today, what: 'Vaga salva'}]`. Returns 201 with the inserted row, 200 if it already existed (return the existing row).
  - `PATCH /api/me/tracked/<job_id>` — body `{stage?, notes?}`. Update `stage` (validate against `STAGE_ORDER`), `notes`. When `stage` changes, append `{when: today, what: 'Movida para <label>'}` to `events`. Bump `updated_at`. Return the updated row.
  - `DELETE /api/me/tracked/<job_id>` — 204 on success, 404 if not found.
- `api/app.py` — small helper `_today_label()` mirroring `useTrackedJobs.js`'s `todayLabel`.
- `api/app.py` — share `STAGE_ORDER` and `STAGE_LABELS` Python-side. Single source of truth: define here, mirror in `web/src/constants/stages.js`. Keep them in sync manually for now (a story to extract later if it drifts).

**Definition of done**

- All four routes round-trip via `curl` with a logged-in session cookie. Cross-user isolation: user A cannot read or delete user B's row (verify with two registered users).
- Trying to set `stage='banana'` returns 400.

**Estimate**: 4h.

### Story 3.3 — Replace `useTrackedJobs` with API-backed hook

**Why**: keep the kit pages (`Dashboard`, `SavedJobs`, `Pipeline`, `TrackedJobModal`) untouched. Only the hook changes shape.

**Files**

- `web/src/hooks/useTrackedJobs.js` — replace the localStorage body. Same return shape: `{trackedJobs, addJob, updateStage, updateNotes, removeJob, isTracked}`.
  - On mount: `GET /api/me/tracked`, set state.
  - `addJob(snapshot)`: optimistic insert into local state, then `POST /api/me/tracked`. On error, rollback and surface a toast (see story 3.5).
  - `updateStage(id, stage)`: optimistic, then `PATCH ../<id>` with `{stage}`. The server returns the updated `events`; replace optimistic state with server's reply.
  - `updateNotes(id, notes)`: same pattern with `{notes}`.
  - `removeJob(id)`: optimistic remove, then `DELETE`.
  - `isTracked(id)`: derived from local state.
- Drop `localStorage.getItem('jh_jobs')` and `setItem` calls. Per decision D, no migration of existing localStorage entries — users will re-save manually.

**Definition of done**

- Logging in as user A, saving a job, logging out, logging in as user B → user B sees an empty tracker.
- Refreshing the page preserves the tracker because it's loaded from the API.
- Network-offline: saving a job shows a transient error via the toast hook.

**Estimate**: 4h.

### Story 3.4 — Toast hook for tracker errors

**Why**: optimistic updates need a way to tell the user "save failed". Today errors only show on the search bar.

**Files**

- `web/src/hooks/useToasts.js` (new) — `{toasts, push, dismiss}`. `push({type:'error'|'info', message})` returns an id; auto-dismiss after 4s.
- `web/src/components/ToastTray.jsx` (new) — renders `toasts` fixed bottom-right. Use `role="status"` + `aria-live="polite"`.
- `web/src/App.js` — mount `<ToastTray />` once, pass `push` to `useTrackedJobs` via context or as a parameter.

**Definition of done**: a forced 500 from the server (temporarily change `addJob` server route to return 500) shows a red toast that disappears after 4s.

**Estimate**: 2h.

### Story 3.5 — Drop the now-unused `useUser` identity bits

**Files**

- `web/src/hooks/useUser.js` — keep only the theme preference (filled in Epic 4). Remove the user-name/email persistence — that lives in the auth payload now.
- `web/src/components/Settings.jsx` — replace the local-only name/email form with a "change password" form (`POST /api/me/password`, body `{current, new}`). New endpoint mirrored in Epic 1 follow-up if needed; otherwise leave the page as a placeholder.

**Definition of done**: Settings shows the logged-in username (read-only) and a change-password form (or a placeholder explaining "em breve").

**Estimate**: 2h.

---

## Epic 4 — Dark theme toggle in the user menu

Goal: a token override system + a toggle in the sidebar foot menu (the existing `<NavItem icon="⚙">`/`<NavItem icon="⏻">` strip).

### Story 4.1 — Define dark-mode design tokens

**Files**

- `web/src/styles/tokens.css` — add a `:root[data-theme="dark"] { ... }` block that overrides `--jh-bg`, `--jh-fg`, `--jh-fg-strong`, `--jh-fg-muted`, `--jh-fg-subtle`, `--jh-border`, `--jh-primary-50`, `--jh-shadow-sm`, `--jh-shadow`, `--jh-shadow-modal`. Keep `--jh-primary` the same; add a slightly lighter `--jh-primary-hover` for contrast.
- Suggested palette (use as a starting point, tweak in browser):
  - `--jh-bg: #0f172a`
  - `--jh-fg: #e2e8f0`
  - `--jh-fg-strong: #f8fafc`
  - `--jh-fg-muted: #94a3b8`
  - `--jh-fg-subtle: #64748b`
  - `--jh-border: #1e293b`
  - `--jh-primary-50: #1e3a8a` (semantic: primary-tinted surface)
- `web/src/App.css` — find spots that hardcode `#fff` or `white` (sidebar, kanban-card, modal, .stat). Replace with `var(--jh-surface)` and add `--jh-surface: #ffffff` to `:root`, `--jh-surface: #1e293b` to dark.
- Same treatment for `#f1f5f9` (kanban-col, hover bgs) → `var(--jh-surface-2)`.

**Definition of done**: setting `<html data-theme="dark">` in DevTools recolours the whole app without obvious white patches.

**Estimate**: 4h (the bulk is auditing existing CSS for hardcoded whites/grays).

### Story 4.2 — `useTheme` hook

**Files**

- `web/src/hooks/useTheme.js` (new):
  - State: `theme` ∈ `{'system','light','dark'}`. Persist to localStorage `jh_theme`.
  - Effect: write `data-theme` attribute on `document.documentElement`. For `'system'`, observe `window.matchMedia('(prefers-color-scheme: dark)')` and mirror its boolean.
  - Return `{theme, setTheme, effective}` where `effective` ∈ `{'light','dark'}`.

**Definition of done**

- `setTheme('dark')` immediately changes the page colours and survives a refresh.
- Setting OS to dark with `theme === 'system'` flips the SPA to dark.

**Estimate**: 2h.

### Story 4.3 — Theme toggle inside the sidebar foot menu

**Files**

- `web/src/components/Sidebar.jsx` — add a third `<NavItem>` inside `.sidebar-foot-actions`, between Configurações and Sair: icon `☾` (or `◐`), label cycling between "Tema: claro" / "Tema: escuro" / "Tema: sistema". Click cycles through the three. Pull the current value from a new `theme` prop. Add `onCycleTheme` prop.
- `web/src/App.js` — call `useTheme()` once and pass `theme` + a cycler down to Sidebar.
- (Optional v2) Replace the cycler with a sub-menu that opens to the right when the foot menu is open.

**Definition of done**

- Clicking the toggle in the menu cycles theme and the sidebar foot label updates.
- The toggle persists across reload.

**Estimate**: 1h.

### Story 4.4 — Visual polish pass

**Files**

- `web/src/styles/shell.css`, `web/src/App.css` — make a second pass after Story 4.1 to fix any contrast or border-mismatch in dark mode. Verify the kanban cards, the JobDetails modal, the JsonTree colour palette, and the tag chips. JsonTree's primitive colours (`.json-string` green, `.json-number` orange, etc.) should still be readable in dark.
- Take screenshots of light and dark for the PR description.

**Definition of done**: WCAG AA contrast on body text in dark mode (use a contrast checker on `--jh-fg` over `--jh-bg`).

**Estimate**: 2h.

---

## Cross-cutting

### Testing & QA

- The project has no automated suite. After each epic, validate manually:
  - `docker compose build api web && docker compose up -d`
  - flake8 strict pass: `docker run --rm -v "$PWD:/src" -w /src python:3.12-slim sh -c 'pip install -q flake8 && flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics'`
  - Browser walkthrough in the PR description (login, save, advance stage, theme toggle, logout, second-user isolation).
- Manually probe with two users to verify isolation in tracker queries.

### Security checklist (run before merge)

- `SECRET_KEY` is required at app start in non-debug mode (no silent fallback).
- Cookies are `HttpOnly` + `SameSite=Lax`. `SESSION_COOKIE_SECURE=true` in any deploy that terminates TLS.
- Login error responses do not enumerate users (same body for "no such user" vs. "wrong password").
- Password validation server-side (clients can be bypassed).
- All `tracked_jobs` queries are scoped by `user_id = ?` — no untrusted user_id from the body.
- No raw SQL string interpolation of user input — every endpoint uses `?` placeholders.

### Out of scope (don't do these in this branch)

- Email-based password reset.
- OAuth / Google sign-in.
- Multi-device session list.
- Migration of existing `localStorage.jh_jobs` (decision D — skipped).
- Black-theme support for the `web/templates/` reference kit (it's static reference).

## Suggested commit cadence

One commit per story, conventional-commits style, e.g.:

```
feat(api): add users table and password hashing helpers
feat(api): add /api/auth register/login/logout/me
feat(api): add @login_required decorator
docs: document auth model in CLAUDE.md
feat(web): add useAuth hook and api client helper
feat(web): replace localStorage gate with real Login form
feat(web): wire logout to /api/auth/logout
feat(api): add tracked_jobs table and migration
feat(api): add /api/me/tracked CRUD endpoints
feat(web): API-backed useTrackedJobs replacing localStorage
feat(web): add toast tray for tracker errors
feat(web): add dark-mode tokens
feat(web): add useTheme hook
feat(web): theme toggle in user menu
chore(web): dark-mode visual polish
```

## Effort summary

- Epic 1 (Auth backend): ~5h
- Epic 2 (Auth frontend): ~5h30
- Epic 3 (Tracker DB): ~13h
- Epic 4 (Theme): ~9h
- Total: ~32h, including buffer for the hardcoded-white CSS audit and toast wiring.
