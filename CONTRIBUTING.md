# Contributing to Calendar Checklist

Thank you for your interest in contributing to Calendar Checklist! This document provides guidelines and information for contributors.

## Getting Started

### Development Environment Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/calendar-checklist.git
   cd calendar-checklist
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies (including dev tools)**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Set up Google Calendar credentials** (optional, for full functionality)
   - Follow the instructions in [README.md](README.md) to set up OAuth credentials
   - The app will run without credentials, but calendar sync will be disabled

### Running the Application

```bash
uvicorn app.main:app --reload
```

Visit http://localhost:8000 to see the application.

## Code Style

This project uses [ruff](https://github.com/astral-sh/ruff) for linting and formatting.

### Linting

```bash
ruff check .
```

### Formatting

```bash
ruff format .
```

### Key Style Guidelines

- Python 3.11+ syntax is encouraged
- Line length: 100 characters
- Use type hints for function parameters and return values
- Follow PEP 8 naming conventions
- SQLAlchemy boolean comparisons use `== True`/`== False` (this is intentional, not `is True`)

## Running Tests

```bash
pytest tests/ -v
```

For coverage report:

```bash
pytest tests/ --cov=app --cov-report=html
```

## Making Changes

### Before You Start

1. Check existing [issues](https://github.com/your-username/calendar-checklist/issues) to see if someone is already working on your idea
2. For significant changes, open an issue first to discuss the approach
3. Fork the repository and create a feature branch

### Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, concise commit messages
   - Add tests for new functionality
   - Update documentation if needed

3. **Run checks before committing**
   ```bash
   ruff check .
   ruff format .
   pytest tests/ -v
   ```

4. **Submit a pull request**
   - Provide a clear description of the changes
   - Reference any related issues
   - Ensure all CI checks pass

## Pull Request Guidelines

### PR Checklist

- [ ] Code follows the project's style guidelines
- [ ] Tests pass locally
- [ ] New code is covered by tests
- [ ] Documentation is updated (if applicable)
- [ ] Commit messages are clear and descriptive

### PR Description Template

```markdown
## Summary
Brief description of the changes.

## Changes
- Change 1
- Change 2

## Testing
How was this tested?

## Related Issues
Fixes #123
```

## Issue Reporting

### Bug Reports

When reporting bugs, please include:

1. **Description**: Clear description of the bug
2. **Steps to Reproduce**: Numbered steps to reproduce the issue
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**: Python version, OS, browser (if applicable)
6. **Logs/Screenshots**: Any relevant error messages or screenshots

### Feature Requests

When requesting features, please include:

1. **Use Case**: Why is this feature needed?
2. **Proposed Solution**: How should it work?
3. **Alternatives Considered**: Other approaches you've thought about

## Project Structure

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

### Quick Reference

| Directory | Purpose |
|-----------|---------|
| `app/core/` | Configuration, database, scheduler |
| `app/calendar/` | Google Calendar integration |
| `app/models/` | SQLModel data models |
| `app/routes/` | FastAPI route handlers |
| `app/templates/` | Jinja2 HTML templates |
| `scripts/` | Utility scripts |
| `tests/` | Test suite |

## Questions?

If you have questions about contributing, feel free to:

1. Open a [discussion](https://github.com/your-username/calendar-checklist/discussions)
2. Check existing issues for similar questions
3. Read the [architecture documentation](docs/ARCHITECTURE.md)

## License

By contributing to Calendar Checklist, you agree that your contributions will be licensed under the MIT License.
