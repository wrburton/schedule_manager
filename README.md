# Calendar Checklist

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A web application that integrates with Google Calendar to present event-based preparation checklists. Helps users confirm readiness for upcoming events by checking required items and attendees, with a verifiable archive of confirmations.

## Features

- Sync events from Google Calendar (polls every 5 minutes)
- Parse checklist items from event descriptions
- Interactive checklists with checkbox toggling
- Confirm readiness when all items are checked
- Archive confirmed events for record-keeping
- Push item changes back to Google Calendar
- Support for recurring events

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLModel, SQLite
- **Frontend:** Jinja2 templates, Tailwind CSS 4 (built by the deploy hooks), Alpine.js, htmx:
  the family apps' stack (see "Front end" below)
- **Scheduler:** APScheduler
- **External:** Google Calendar API v3

The family's copy runs on the home server at https://<home domain>/schedule/
(home network only) and is deployed with `git push live main`: see "Deployment" below.

## Quick Start

### 1. Clone and Install

```bash
cd schedule_manager
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

### 2. Set Up Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Calendar API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click "Enable"

### 3. Create OAuth Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - User Type: External (or Internal if using Google Workspace)
   - App name: "Calendar Checklist"
   - Add your email as a test user
4. Create OAuth client ID:
   - **Application type: Desktop app** (NOT Web application)
   - Name: "Calendar Checklist"
5. Copy the Client ID and Client Secret

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_CALENDAR_ID=primary
```

**Finding your Calendar ID:**
- For your primary calendar: use `primary`
- For a shared/family calendar:
  1. Open Google Calendar
  2. Click the three dots next to the calendar name
  3. Select "Settings and sharing"
  4. Scroll to "Integrate calendar"
  5. Copy the "Calendar ID"

### 5. Get Refresh Token

Run the setup script to authenticate and get a refresh token:

```bash
python scripts/get_token.py
```

This will:
1. Open a browser window for Google authentication
2. Ask you to authorize calendar access
3. Display a `GOOGLE_REFRESH_TOKEN` to add to your `.env` file

Copy the token to your `.env`:

```env
GOOGLE_REFRESH_TOKEN=1//your-refresh-token-here
```

### 6. Run the Application

Generate a self-signed certificate:

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

Start the server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

Open https://localhost:8000 (or your server's IP) in your browser.

## Usage

### Adding Checklist Items

**Method 1: In Google Calendar**

Add items to your event description using this format:

```
Items:
- Laptop
- Charger
- Meeting notes
```

Also supports: `Checklist:`, `Things to bring:`, `Required:`, `Bring:`, `Pack:`

**Method 2: In the App**

Use the "Add item" form on any event page.

### Confirming Events

1. Check all items on the checklist
2. Click "Confirm Ready"
3. The event is marked as confirmed

### Archiving Events

Click "Archive" to move an event to the archive. Archived events are read-only but preserved for reference.

## Event Description Format

The app parses checklist items from event descriptions. Supported formats:

```
Items:
- Item 1
- Item 2

Checklist:
* Task A
* Task B

Things to bring:
[ ] Unchecked item
[x] Checked item
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/events/upcoming` | List upcoming events |
| GET | `/events/archive` | List archived events |
| GET | `/events/{id}` | Event detail view |
| POST | `/events/{id}/confirm` | Confirm checklist complete |
| POST | `/events/{id}/archive` | Archive event |
| POST | `/events/{id}/items` | Add item to checklist |
| POST | `/events/{id}/items/{item_id}/toggle` | Toggle item checked |
| POST | `/events/{id}/items/{item_id}/delete` | Delete item |
| POST | `/events/{id}/items/push` | Push items to Google Calendar |
| POST | `/sync/now` | Trigger manual sync |
| GET | `/sync/status` | Get sync status |
| GET | `/auth/status` | Check credential status |
| GET | `/auth/setup` | View setup instructions |

## Configuration

Environment variables (`.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | Calendar Checklist |
| `DEBUG` | Enable debug mode | false |
| `SECRET_KEY` | Secret key for sessions | (required) |
| `HOST` | Server bind address | 0.0.0.0 |
| `PORT` | Server port | 8000 |
| `ALLOWED_ORIGINS` | CORS origins (comma-separated or *) | * |
| `DATABASE_URL` | SQLite database path | sqlite:///./calendar_checklist.db |
| `GOOGLE_CLIENT_ID` | OAuth client ID | (required) |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret | (required) |
| `GOOGLE_REFRESH_TOKEN` | OAuth refresh token | (required - from get_token.py) |
| `GOOGLE_CALENDAR_ID` | Calendar to sync | primary |
| `SYNC_INTERVAL_MINUTES` | Background sync interval | 5 |

## Development

### Running Tests

```bash
pip install -c constraints.txt -e ".[dev]"
pytest tests/ -v
```

`constraints.txt` pins the exact versions running on the server; change a dependency in
`pyproject.toml` and its pin there in the same commit.

### Front end

The family apps' rules, enforced by `tests/test_frontend.py`:

- **Styling**: Tailwind v4 classes in templates, plus the component classes in
  `app/static/css/src/components.css`; the theme (the family's dark palette with a violet
  accent) is in `app/static/css/src/app.css`. No `<style>` blocks, no CDN. The CSS is built
  on the server by `scripts/build_css.sh` (Tailwind CLI 4.3.3) from the deploy hooks; the
  output `app/static/css/app.css` is never committed.
- **Behaviour**: Alpine.js components in `app/static/js/app.js` (`tabRefresh` reloads an
  events page when you return to the tab after a minute away; `x-confirm`), and htmx:
  ticking an item posts with `hx-post` and the server returns the re-rendered card
  (`_event_card.html` on the upcoming page, `_event_detail_card.html` on an event's page).
  Every form still works without JavaScript (post and redirect). No inline `<script>` or
  `on*=""` handlers. Alpine 3.17.2 and htmx 2.0.4 are vendored in `app/static/js/`.
- To look at a change locally, build the CSS on the server and copy it back (the CLI isn't
  installed on Windows): see the dinner planner's README, "Front end", with `app/static`
  in place of `static`.

## Deployment

The family's copy runs on the home server (servertools' SERVER.md has the details), deployed like the
other family apps (since 2026-10-25). Code is changed in a clone on the PC and pushed to the
live checkout `~/share/schedule_manager` (remote `live`, branch `main`); hooks on the server
test, snapshot, build and restart. The tests are the gate; there's no staging copy.

```
PC clone (calendar\schedule_manager)  ──git push live main (or srv deploy)──►  ~/share/schedule_manager
                                       pre-receive: direct-edit guard, tests on a /tmp export,
                                                    CSS build, snapshot of calendar_checklist.db
                                       post-receive: deps, CSS build, unit, restart, health check,
                                                     mirror main to GitHub (deploy.mirror)
https://<home domain>/schedule/ ◄── Caddy ── uvicorn 127.0.0.1:8000 (--root-path /schedule)
```

- **Service**: the user-level unit `schedule_manager.service` (`deploy/`, installed by
  `scripts/install_service.sh`, which also removed the old system unit and set `.env` to 600).
  `srv status calendar`, `srv logs calendar`, `srv restart calendar`.
- **GitHub** (`origin`, wrburton/schedule_manager) is a mirror: post-receive pushes `main`
  there after each deploy when `git config deploy.mirror origin` is set in the live checkout
  (the PC can't reach GitHub; the server can).
- **Backups**: each deploy snapshots the database to `backups/pre-deploy/` (newest 20), and
  `servertools-backup@schedule_manager.timer` copies it to the NAS nightly
  (`calendar-backup/db/`, 60 days).
- **Rules**: never edit tracked files in `~/share/schedule_manager` (a dirty live tree blocks
  every push); undo with a revert commit (force-push is refused); `.env` holds the Google
  refresh token and stays on the server.

### Project Structure

```
schedule_manager/
├── app/
│   ├── main.py              # Application entry point
│   ├── core/
│   │   ├── config.py        # Settings management
│   │   ├── database.py      # Database setup
│   │   └── scheduler.py     # Background job scheduler
│   ├── calendar/
│   │   ├── client.py        # Google Calendar API client
│   │   ├── parser.py        # Description parser
│   │   └── sync.py          # Sync service
│   ├── models/              # SQLModel data models
│   ├── routes/              # FastAPI route handlers
│   ├── web.py               # The shared templates object and rp(request)
│   ├── static/              # css/src (Tailwind sources), js (app.js, Alpine, htmx), favicon
│   └── templates/           # Jinja2 templates (_event_card.html etc. are htmx partials)
├── deploy/                  # The user-level systemd unit
├── scripts/
│   ├── get_token.py         # One-time OAuth setup script
│   ├── build_css.sh         # Tailwind build (run by the hooks)
│   ├── install_service.sh   # Installs the systemd unit on the server
│   └── git-hooks/           # pre-receive / post-receive
├── tests/
├── pyproject.toml
└── README.md
```

## Sync & Conflict Rules

- **Google Calendar is the source of truth** for event definitions
- **Local database is the source of truth** for checklist state
- Event time change → checklist is reset (items unchecked)
- Item list change in description → new items added, removed items deleted
- Confirmed events are never modified by sync
- Archived events are read-only

## Troubleshooting

### "No valid credentials" error

Run `python scripts/get_token.py` to get a new refresh token and update your `.env` file.

### Token expired

Google refresh tokens are long-lived but can expire if:
- Not used for 6 months
- User revokes access
- You exceed 50 refresh tokens per account

Re-run `python scripts/get_token.py` to get a new token.

### Can't access from other devices

Make sure:
1. `HOST=0.0.0.0` in your `.env`
2. Firewall allows port 8000
3. Access via the server's IP address, not localhost

## API Documentation

The application provides interactive API documentation:

- **Swagger UI**: Visit `/docs` for interactive API exploration
- **ReDoc**: Visit `/redoc` for alternative API documentation

All endpoints are documented with request/response examples.

## Documentation

- [Architecture Guide](docs/ARCHITECTURE.md) - System design, data flows, and technical details
- [Contributing Guide](CONTRIBUTING.md) - How to contribute to the project
- [Changelog](CHANGELOG.md) - Version history and release notes

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- Setting up your development environment
- Code style guidelines (we use ruff for linting)
- Running tests
- Submitting pull requests

## License

MIT - see [LICENSE](LICENSE) for details.
