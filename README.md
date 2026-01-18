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
- **Frontend:** Jinja2 templates, Tailwind CSS
- **Scheduler:** APScheduler
- **External:** Google Calendar API v3

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
pip install -e ".[dev]"
pytest tests/ -v
```

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
│   └── templates/           # Jinja2 HTML templates
├── scripts/
│   └── get_token.py         # One-time OAuth setup script
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
