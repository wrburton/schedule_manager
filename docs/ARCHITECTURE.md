# Calendar Checklist - Architecture Documentation

This document describes the end-to-end architecture and data flows of the Calendar Checklist application.

## Getting Started for Contributors

This section provides a quick orientation for developers new to the codebase.

### Key Concepts

1. **Events** are synced from Google Calendar and stored locally with associated checklists
2. **Items** are checklist entries that can be parsed from event descriptions or added manually
3. **Sync** is bidirectional: events come from Google, but item changes can be pushed back
4. **Confirmations** create an audit trail when a user marks a checklist as complete

### Where to Find Things

| I want to... | Look in... |
|-------------|-----------|
| Add a new API endpoint | `app/routes/` |
| Modify the data models | `app/models/` |
| Change sync behavior | `app/calendar/sync.py` |
| Update the UI | `app/templates/` |
| Modify app configuration | `app/core/config.py` |
| Add background jobs | `app/core/scheduler.py` |
| Write tests | `tests/` |

### Development Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the app
uvicorn app.main:app --reload

# Run tests
pytest tests/ -v

# Check code style
ruff check .
```

---

## Overview

Calendar Checklist is a web application that integrates with Google Calendar to present event-based preparation checklists. It syncs events from Google Calendar, parses checklist items from event descriptions, and provides an interactive interface for users to confirm readiness for upcoming events.

```
+-------------------------------------------------------------------------+
|                           User Browser                                   |
|  +--------------+  +--------------+  +--------------+  +--------------+ |
|  |  Upcoming    |  |   Event      |  |   Archive    |  |    Auth      | |
|  |   Events     |  |   Detail     |  |    View      |  |   Setup      | |
|  +------+-------+  +------+-------+  +------+-------+  +------+-------+ |
+---------+----------------+----------------+----------------+-------------+
          |                |                |                |
          v                v                v                v
+-------------------------------------------------------------------------+
|                         FastAPI Application                              |
|  +-------------------------------------------------------------------+  |
|  |                        Route Handlers                             |  |
|  |   /events/*    /events/{id}/items/*    /sync/*    /auth/*        |  |
|  +-------------------------------------------------------------------+  |
|                              |                                          |
|  +---------------------------+-----------------------------------+      |
|  |                     Core Services                              |     |
|  |  +-----------+  +-----------+  +---------------------+         |     |
|  |  | Database  |  | Scheduler |  |  Calendar Client    |         |     |
|  |  | (SQLite)  |  |(APScheduler)| (Google API)         |         |     |
|  |  +-----+-----+  +-----+-----+  +----------+----------+         |     |
|  +--------+---------------+-------------------+--------------------+    |
+-----------+---------------+-------------------+-------------------------+
            |               |                   |
            v               |                   v
+---------------------+     |     +-----------------------------------+
|  calendar_checklist |     |     |     Google Calendar API v3        |
|       .db           |     |     |                                   |
|  +---------------+  |     |     |  - List events                    |
|  |    Events     |  |     |     |  - Update descriptions            |
|  |    Items      |  |<----+     |  - OAuth2 authentication          |
|  |   Attendees   |  |           +-----------------------------------+
|  | Confirmations |  |
|  +---------------+  |
+---------------------+
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Web Framework | FastAPI | Routing, validation, async support |
| Database | SQLite + WAL | Persistent storage |
| ORM | SQLModel | Type-safe models (Pydantic + SQLAlchemy) |
| Configuration | Pydantic Settings | Environment-based config |
| Scheduler | APScheduler | Background sync jobs |
| Templates | Jinja2 | Server-side HTML rendering |
| Styling | Tailwind CSS | Utility-first CSS framework |
| Calendar API | google-api-python-client | Google Calendar integration |
| Authentication | Google OAuth2 | API authorization |

## Project Structure

```
schedule_manager/
├── app/
│   ├── main.py                 # Application entry point, lifespan management
│   ├── core/
│   │   ├── config.py           # Settings from environment variables
│   │   ├── database.py         # SQLite engine, session management
│   │   └── scheduler.py        # APScheduler background jobs
│   ├── calendar/
│   │   ├── client.py           # Google Calendar API client, OAuth
│   │   ├── parser.py           # Description parsing for checklist items
│   │   └── sync.py             # Bidirectional sync logic
│   ├── models/
│   │   ├── event.py            # Event model
│   │   ├── item.py             # Checklist item model
│   │   ├── attendee.py         # Attendee model
│   │   ├── confirmation.py     # Confirmation record model
│   │   └── oauth.py            # OAuth token model
│   ├── routes/
│   │   ├── auth.py             # Authentication status, setup
│   │   ├── events.py           # Event listing, confirmation, archiving
│   │   ├── items.py            # Checklist item CRUD, toggle
│   │   └── sync.py             # Manual sync trigger, status
│   └── templates/
│       ├── base.html           # Layout, navigation, JavaScript
│       ├── events.html         # Upcoming events view
│       ├── event_detail.html   # Single event view
│       ├── archive.html        # Archived events view
│       └── auth_setup.html     # OAuth setup instructions
├── docs/
│   └── ARCHITECTURE.md         # This file
├── scripts/
│   └── get_token.py            # One-time OAuth token acquisition
├── tests/
├── pyproject.toml
└── README.md
```

## Data Models

### Entity Relationship Diagram

```
+----------------------+
|        Event         |
+----------------------+
| id (PK)              |
| google_event_id (UK) |
| recurring_event_id   |
| title                |
| description          |
| start_time           |
| end_time             |
| last_synced          |
| is_archived          |
| user_id              |
+----------+-----------+
           |
           | 1:N
           |
     +-----+-----+-------------+
     |           |             |
     v           v             v
+---------+ +----------+ +--------------------+
|  Item   | | Attendee | |ChecklistConfirmation|
+---------+ +----------+ +--------------------+
| id (PK) | | id (PK)  | | id (PK)            |
| event_id| | event_id | | event_id (FK)      |
| name    | | email    | | confirmed_at       |
|is_checked| |display_  | | confirmed_by       |
| source  | |  name    | +--------------------+
+---------+ |response_ |
            |  status  |
            +----------+
```

### Model Details

**Event**
- Primary key: UUID
- Unique constraint on `google_event_id`
- Tracks sync state with `last_synced` timestamp
- `is_archived` flag prevents modifications

**Item**
- Foreign key to Event (cascade delete)
- `source` field: "parsed" (from description) or "manual" (user-added)
- Manual items protected from sync deletion

**Attendee**
- Foreign key to Event (cascade delete)
- `response_status`: accepted, declined, tentative, needsAction

**ChecklistConfirmation**
- Foreign key to Event
- Records when checklist was confirmed complete
- `confirmed_at` auto-set on creation

## Application Lifecycle

### Startup Sequence

```
Application Start
       |
       v
+----------------------+
| create_db_and_tables |  Create SQLite database and tables
+----------+-----------+
           |
           v
+----------------------+
|   start_scheduler    |  Initialize APScheduler with sync job
+----------+-----------+
           |
           v
+----------------------+
|   Mount Routers      |  Register route handlers
+----------+-----------+
           |
           v
+----------------------+
|   Ready for Requests |
+----------------------+
```

### Shutdown Sequence

```
Shutdown Signal
       |
       v
+----------------------+
|  shutdown_scheduler  |  Stop background jobs gracefully
+----------+-----------+
           |
           v
+----------------------+
|   Close Connections  |  Release database connections
+----------------------+
```

## Data Flows

### 1. Background Sync Flow

The scheduler triggers a sync every 5 minutes (configurable).

```
+-------------+
| APScheduler | Every 5 minutes
+------+------+
       |
       v
+------------------+
|   sync_job()     |
+--------+---------+
         |
         v
+------------------------+
|  sync_calendar()       |
+--------+---------------+
         |
         v
+------------------------------------------------+
|              Google Calendar API                |
|  events.list(calendarId, timeMin, timeMax,     |
|              syncToken?, singleEvents=True)     |
+--------+---------------------------------------+
         |
         v
+------------------------------------------------+
|           For each event in response:           |
|                                                 |
|  +---------------------------------------------+
|  | Event cancelled?                            |
|  |   YES -> _handle_deleted_event()            |
|  |   NO  -> _upsert_event()                    |
|  |         +-- Update event fields             |
|  |         +-- _sync_items() from description  |
|  |         +-- _sync_attendees()               |
|  +---------------------------------------------+
+--------+---------------------------------------+
         |
         v
+------------------------+
|  Store nextSyncToken   |  For incremental sync next time
+------------------------+
```

### 2. Checkbox Toggle Flow (AJAX)

User clicks a checkbox for instant feedback.

```
+-----------------------------------------------------------------+
|                        Browser                                   |
|                                                                  |
|  User clicks checkbox                                            |
|         |                                                        |
|         v                                                        |
|  +----------------------------------------------------------+   |
|  | JavaScript: Optimistic Update                             |   |
|  |  - Toggle checkbox visual immediately                     |   |
|  |  - Update text strikethrough                              |   |
|  |  - Disable button during request                          |   |
|  +------------------------+----------------------------------+   |
|                           |                                      |
|                           | POST /events/{id}/items/{id}/toggle  |
|                           | Accept: application/json             |
+---------------------------+--------------------------------------+
                            |
                            v
+-------------------------------------------------------------------+
|                      FastAPI Handler                               |
|                                                                    |
|  1. Validate item and event exist                                  |
|  2. Check event not archived                                       |
|  3. Toggle: item.is_checked = not item.is_checked                  |
|  4. Commit to database                                             |
|  5. Calculate counts for response                                  |
|                                                                    |
|  Return JSON:                                                      |
|  {                                                                 |
|    "success": true,                                                |
|    "is_checked": true/false,                                       |
|    "checked_count": N,                                             |
|    "total_count": M,                                               |
|    "all_checked": true/false                                       |
|  }                                                                 |
+----------------------------+--------------------------------------+
                             |
                             v
+-------------------------------------------------------------------+
|                        Browser                                     |
|                                                                    |
|  +------------------------------------------------------------+   |
|  | JavaScript: Handle Response                                 |   |
|  |  - Update item counter (N/M)                                |   |
|  |  - Enable/disable "Confirm Ready" button based on all_checked  |
|  |  - Re-enable checkbox button                                |   |
|  +------------------------------------------------------------+   |
|                                                                    |
|  On Error:                                                         |
|  +------------------------------------------------------------+   |
|  |  - Rollback optimistic update                               |   |
|  |  - Log error to console                                     |   |
|  +------------------------------------------------------------+   |
+-------------------------------------------------------------------+
```

### 3. Event Confirmation Flow

User confirms all checklist items are complete.

```
+------------------+
| User clicks      |
| "Confirm Ready"  |
+--------+---------+
         |
         v
+----------------------------------------+
|  POST /events/{event_id}/confirm       |
+--------+-------------------------------+
         |
         v
+----------------------------------------+
|           Validation                    |
|  - Event exists?                        |
|  - Event not archived?                  |
|  - All items checked?                   |
+--------+----------------------+--------+
         |                      |
    All pass               Validation failed
         |                      |
         v                      v
+---------------------+  +-----------------+
| Create Confirmation |  | Return 400 Bad  |
| Record              |  | Request         |
| - event_id          |  +-----------------+
| - confirmed_at=now  |
| - confirmed_by=1    |
+--------+------------+
         |
         v
+---------------------+
| Redirect to event   |
| detail page         |
+---------------------+
```

### 4. Push to Calendar Flow

User pushes local checklist changes back to Google Calendar.

```
+----------------------+
| User clicks          |
| "Push to Calendar"   |
+--------+-------------+
         |
         v
+----------------------------------------+
|  POST /events/{event_id}/items/push    |
+--------+-------------------------------+
         |
         v
+----------------------------------------+
|  push_items_to_calendar(event)         |
|                                        |
|  1. Get current Google event           |
|  2. Format items to description section|
|  3. Preserve non-items description text|
|  4. PATCH event description            |
+--------+-------------------------------+
         |
         v
+----------------------------------------+
|         Google Calendar API            |
|  events.patch(calendarId, eventId,     |
|               body={description: ...}) |
+--------+-------------------------------+
         |
         v
+----------------------------------------+
|  Redirect to event detail              |
|  (Shows updated description)           |
+----------------------------------------+
```

## Sync Conflict Resolution

The application follows these rules to resolve conflicts between Google Calendar and local database:

### Source of Truth Rules

| Data Type | Source of Truth | Notes |
|-----------|-----------------|-------|
| Event title, times | Google Calendar | Always synced from Google |
| Event description | Google Calendar | Items parsed from description |
| Checklist item state | Local Database | `is_checked` preserved during sync |
| Manual items | Local Database | Never deleted by sync |
| Confirmations | Local Database | Immutable once created |

### Conflict Scenarios

**1. Event Time Changed**
```
Google Calendar: Event time modified
                      |
                      v
            +---------------------+
            | Reset all items to  |
            | is_checked = false  |
            +---------------------+
```
Rationale: A rescheduled event may require re-preparation.

**2. Description Items Changed**
```
Google Calendar: Description modified
                      |
                      v
            +-----------------------------+
            | Compare parsed items with   |
            | existing source="parsed"    |
            |                             |
            | New items -> Add to database|
            | Removed items -> Delete     |
            | Existing items -> Keep state|
            +-----------------------------+
```

**3. Manual Items**
```
User adds item via UI (source="manual")
                      |
                      v
            +-----------------------------+
            | Manual items NEVER deleted  |
            | by sync process             |
            +-----------------------------+
```

**4. Archived Events**
```
Event is archived
        |
        v
+---------------------------------+
| Sync skips all modifications    |
| Event preserved in current state|
+---------------------------------+
```

## Authentication Flow

The application uses Google OAuth2 with a pre-authorized refresh token.

### Initial Setup (One-time)

```
+---------------------+
| scripts/get_token.py|
+--------+------------+
         |
         v
+-----------------------------------------+
| Open browser for Google OAuth consent   |
| - User authorizes calendar access       |
| - Scopes: calendar.readonly,            |
|           calendar.events               |
+--------+--------------------------------+
         |
         v
+-----------------------------------------+
| Receive authorization code              |
| Exchange for refresh token              |
+--------+--------------------------------+
         |
         v
+-----------------------------------------+
| Display refresh token                   |
| User copies to .env file                |
+-----------------------------------------+
```

### Runtime Authentication

```
+-----------------------------------------+
|         get_credentials()               |
+--------+--------------------------------+
         |
         v
+-----------------------------------------+
| Check cached credentials                |
|                                         |
| If valid and not expired:               |
|   Return cached credentials             |
|                                         |
| If expired or missing:                  |
|   Create new Credentials from           |
|   refresh_token in environment          |
|   |                                     |
|   v                                     |
|   Auto-refresh access token             |
|   Cache credentials                     |
|   Return credentials                    |
+-----------------------------------------+
```

## API Reference

### Events

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/events/upcoming` | List upcoming events | HTML |
| GET | `/events/archive` | List archived events | HTML |
| GET | `/events/{id}` | Event detail view | HTML |
| POST | `/events/{id}/confirm` | Confirm checklist complete | Redirect |
| POST | `/events/{id}/archive` | Archive event | Redirect |
| POST | `/events/{id}/unarchive` | Unarchive event | Redirect |

### Items

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| POST | `/events/{id}/items` | Add item | Redirect |
| POST | `/events/{id}/items/{item_id}/toggle` | Toggle checked | JSON or Redirect |
| POST | `/events/{id}/items/{item_id}/delete` | Delete item | Redirect |
| POST | `/events/{id}/items/push` | Push to Google Calendar | Redirect |

### Sync

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| POST | `/sync/now` | Trigger manual sync | Redirect |
| GET | `/sync/status` | Get sync status | JSON |

### Auth

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/auth/status` | Check authentication | JSON |
| GET | `/auth/setup` | Setup instructions | HTML |

### System

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/` | Redirect to upcoming | Redirect |
| GET | `/health` | Health check | JSON |

## Configuration

All configuration is managed through environment variables (`.env` file).

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | Calendar Checklist | Application display name |
| `DEBUG` | false | Enable debug logging |
| `SECRET_KEY` | change-me-in-production | Session encryption key |
| `HOST` | 0.0.0.0 | Server bind address |
| `PORT` | 8000 | Server port |
| `ALLOWED_ORIGINS` | * | CORS allowed origins |
| `DATABASE_URL` | sqlite:///./calendar_checklist.db | Database connection |
| `GOOGLE_CLIENT_ID` | (required) | OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | (required) | OAuth client secret |
| `GOOGLE_REFRESH_TOKEN` | (required) | Long-lived refresh token |
| `GOOGLE_CALENDAR_ID` | primary | Calendar to sync |
| `SYNC_INTERVAL_MINUTES` | 5 | Background sync frequency |

## Error Handling

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | GET requests |
| 303 | See Other | POST redirect after success |
| 400 | Bad Request | Attempting to modify archived event |
| 404 | Not Found | Event or item doesn't exist |
| 500 | Server Error | Google API failure |

### Graceful Degradation

- **No credentials**: App runs, shows setup instructions, sync disabled
- **Sync failure**: Error logged, app continues, retry on next interval
- **JavaScript disabled**: Forms fall back to full page reload
- **Google API error**: Logged, sync token reset for full sync on retry

## Security Considerations

1. **Database**: Foreign keys enforced, WAL mode for safe concurrent access
2. **CORS**: Configurable allowed origins (default permissive for development)
3. **OAuth**: Refresh token stored in environment, not database
4. **Input Validation**: Pydantic models validate all input
5. **SQL Injection**: SQLModel/SQLAlchemy ORM prevents injection
6. **XSS**: Jinja2 auto-escapes template output

## Performance Optimizations

1. **Incremental Sync**: Uses Google's sync tokens to fetch only changes
2. **Credential Caching**: OAuth credentials cached in memory
3. **Service Caching**: Google API service instance reused
4. **AJAX Updates**: Checkbox toggles don't require page reload
5. **Optimistic UI**: Immediate visual feedback before server response
6. **SQLite WAL**: Write-Ahead Logging for concurrent read performance
