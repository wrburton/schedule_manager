# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-01-01

### Added

- Initial release of Calendar Checklist
- Google Calendar integration with OAuth2 authentication
- Background sync every 5 minutes using APScheduler
- Event display with two-tier view (soon vs later)
- Checklist item parsing from event descriptions
- Manual item creation via web UI
- Item toggle with AJAX for instant feedback
- Confirmation workflow with audit trail
- Event archiving for historical reference
- Push changes back to Google Calendar
- Recurring event support with master event propagation
- SQLite database with WAL mode for concurrent access
- Tailwind CSS styling with responsive design
- Touch-friendly interface optimized for tablets

### Technical

- FastAPI web framework with async support
- SQLModel ORM for type-safe database operations
- Pydantic Settings for configuration management
- Jinja2 templates for server-side rendering
- Google Calendar API v3 integration

[Unreleased]: https://github.com/your-username/calendar-checklist/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-username/calendar-checklist/releases/tag/v0.1.0
