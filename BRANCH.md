# `feature/design-ui-kit` — branch summary

PR: [#53](https://github.com/abnerrizzi/jobhubmine/pull/53) — base `feature/design`.

Folds the design kit (formerly `ui_kits/jobhub_app/`, now relocated to `web/templates/jobhub_app/` for reference only) into the CRA web app while keeping the existing API-backed search/filter/table flow intact.

## What's new in the UI

- **Sidebar shell** at 240px with five pages: Dashboard, Buscar vagas (the existing search), Salvas, Pipeline (kanban), and a collapsible user menu in the foot (Configurações + Sair).
- **Login gate** (localStorage-only) collects a display name; "Sair" wipes `jh_authed` + `jh_user`.
- **Browse stays mounted** via `display: none` on nav-switch so search/filter/scroll/pagination state survives.
- **Tracker pages** run on a localStorage cache (`jh_jobs`) — no new API endpoints.
- **Save bridge**: heart on each `JobTable` row and a "Salvar vaga" button in `JobDetails` toggle a job in/out of the tracker.
- **JobDetails is the primary modal everywhere** — clicking a tracked job in Dashboard / Saved / Pipeline opens it (with URL, Sync, JsonTree). The notes/timeline modal (`TrackedJobModal`) is reached via a "Anotações e linha do tempo" button inside `JobDetails` when the job is saved.
- **Filter widths standardized** — 180px default, 360px for Empresa and Departamento.

## Files touched

### New

- `web/public/logo-monogram.svg`
- `web/src/styles/tokens.css` — defines `--jh-*` design tokens; aliases the legacy `--primary`/`--bg-color`/etc. onto them.
- `web/src/styles/shell.css` — port of kit `app.css`.
- `web/src/constants/stages.js` — `STAGE_META`, `STAGE_ORDER`, `STAGE_NEXT`.
- `web/src/hooks/useTrackedJobs.js` — localStorage tracker (add / updateStage / updateNotes / removeJob / isTracked) with quota-error guard.
- `web/src/hooks/useUser.js` — persona persisted to `jh_user`.
- `web/src/hooks/useModalA11y.js` — ESC-to-close, focus-on-open, focus-restore, `role="dialog" aria-modal="true"`. Reused by both modals.
- `web/src/components/Sidebar.jsx` — nav shell + collapsible foot menu (user row toggles Configurações + Sair, closes on outside-click and ESC).
- `web/src/components/Login.jsx` — onboarding screen.
- `web/src/components/Dashboard.jsx` — stats grid + recent activity over tracker.
- `web/src/components/SavedJobs.jsx` — list of jobs in `salva` stage.
- `web/src/components/Pipeline.jsx` — kanban with HTML5 drag-and-drop **plus** a per-card `<select>` keyboard fallback. Uses `text/plain` MIME for the DnD payload.
- `web/src/components/Settings.jsx` — name / email controlled inputs.
- `web/src/components/TrackedJobModal.jsx` — notes textarea (`onBlur`-persist), timeline, advance-stage.

### Modified

- `web/src/App.js` — page state + auth gate + tracker hooks; renders all five pages; auto-closes modals on nav-switch; defers browse API calls until first visit; opens `JobDetails` for tracker rows (with sequence-guarded API refresh).
- `web/src/App.css` — body/shell rules removed (handled by `tokens.css` + `shell.css`); page-specific styles preserved.
- `web/src/index.js` — cascades `tokens.css` → `shell.css` → `App.css`.
- `web/src/components/JobTable.jsx` — heart icon button per row, `aria-pressed`, click toggles save.
- `web/src/components/JobDetails.jsx` — Salvar/Remover toggle, "Anotações e linha do tempo" button (when saved), a11y wiring via `useModalA11y`.
- `web/src/components/FilterBar.jsx` — widths via `filter-select` / `filter-select-wide` classes.

### Moved

- `ui_kits/jobhub_app/` → `web/templates/jobhub_app/` (reference only; not bundled — Dockerfile copies just `src/` and `public/`).

## Decisions worth remembering

- **No `react-router-dom`** — page state in `App.js` is enough.
- **No new API endpoints** for saved/stage/notes — localStorage is the v1 store.
- **Two modals, one bridge** — `JobDetails` (API-backed: Sync, JsonTree, DOMPurify) and `TrackedJobModal` (local: notes, timeline) stay separate; bridged by the in-modal button.
- **String IDs end-to-end** — LinkedIn UUIDs survive the kanban drag round-trip.
- **`tokens.css` aliases legacy vars** onto `--jh-*` so the existing search/table CSS keeps rendering unchanged.

## Build & verify

```
docker compose build web
docker run --rm -v "$PWD:/src" -w /src python:3.12-slim sh -c \
  'pip install -q flake8 && flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics'
docker compose up -d   # http://localhost:8080
```

## Commit log

```
9839bdb feat(web): collapse sidebar foot actions behind user menu
b1a44fa feat(web): move Configuracoes to sidebar foot and add Sair action
9ee02bb style(web): standardize filter widths, double-width for company and department
097a0b9 feat(web): open JobDetails as primary modal from tracker rows
cefed3d fix(web): allow unsaving by clicking saved heart or button
73e2f58 fix(web): use aria-pressed on save buttons and text/plain dnd type
c3cca9a fix(web): clear user identity on logout
d38a4ef perf(web): defer browse api fetches until tab visited
f2f7d1e fix(web): close modals on sidebar nav switch
e4a65d2 chore: move ui_kits/ to web/templates/
19ee780 feat(web): wire ui_kit shell into App.js with login gate
bf401c7 feat(web): add save-job bridge to JobTable and JobDetails
fc81fb8 feat(web): add TrackedJobModal with notes, timeline and detail bridge
fe0bb81 feat(web): add Dashboard, SavedJobs, Pipeline and Settings pages
b3bb238 feat(web): add Sidebar nav shell and Login gate
9008160 feat(web): add tracked-jobs/user/modal-a11y hooks
c792aba feat(web): add ui_kit design tokens, shell css, monogram, stages
```
