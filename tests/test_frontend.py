"""Guards for the front end: Tailwind for styling, Alpine.js and htmx for behaviour.

The family apps' rules (finance, medical, synchro, email, dinner): the CSS is
built on the server by the deploy hooks, so these keep the templates to what
that build expects.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "app" / "templates"
STATIC = ROOT / "app" / "static"
CSS = STATIC / "css"
JS = STATIC / "js"
APP_SCRIPTS = [JS / "app.js"]


def templates() -> list[tuple[str, str]]:
    return [(str(p.relative_to(TEMPLATES)), p.read_text(encoding="utf-8")) for p in sorted(TEMPLATES.rglob("*.html"))]


def test_pages_load_the_built_stylesheet_and_no_cdn() -> None:
    base = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    assert "/static/css/app.css" in base
    assert [name for name, text in templates() if re.search(r"https?://cdn\.|unpkg\.com|jsdelivr", text)] == []
    assert sorted(p.name for p in CSS.glob("*.css")) in ([], ["app.css"])


def test_pages_extend_the_base_template() -> None:
    pages = [(name, text) for name, text in templates() if not Path(name).name.startswith("_") and name != "base.html"]
    assert pages and all('{% extends "base.html" %}' in text for _, text in pages)


def test_tailwind_entry_point() -> None:
    src = (CSS / "src" / "app.css").read_text(encoding="utf-8")
    assert "@layer theme, base, components, utilities;" in src
    assert '@import "./components.css" layer(components);' in src
    assert not re.search(r'@import\s+"tailwindcss"\s*[;\s]', src)
    assert "@theme static" in src and "--color-*: initial;" in src
    assert '@source "../../../templates";' in src
    for script in APP_SCRIPTS:
        assert f'@source "../../js/{script.name}";' in src


def test_static_files_are_revalidated(client) -> None:
    response = client.get("/static/js/app.js")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache"


def test_templates_have_no_style_blocks() -> None:
    assert [name for name, text in templates() if re.search(r"<style[\s>]", text)] == []


def test_inline_styles_only_carry_data() -> None:
    offenders = [f"{name}: {style}" for name, text in templates()
                 for style in re.findall(r'(?<![\w:-])style="([^"]*)"', text) if "{{" not in style]
    assert offenders == []


def theme_colours() -> set[str]:
    return set(re.findall(r"--color-([a-z0-9-]+):", (CSS / "src" / "app.css").read_text(encoding="utf-8")))


COLOUR_CLASS = re.compile(
    r"(?<![\w-])(?:hover:|focus:)?(?:text|bg|border(?:-[tblrxy])?|ring|outline|fill|stroke|from|to|via|divide|placeholder|accent|caret|decoration)"
    r"-((?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}"
    r"|primary(?:-hover)?|fg|muted|dim|faint|page|surface(?:-hover)?|line(?:-inner)?|white|black)(?:/\d+)?(?![\w-])")


def test_colour_classes_exist_in_the_theme() -> None:
    known = theme_colours()
    sources = templates() + [(p.name, p.read_text(encoding="utf-8")) for p in APP_SCRIPTS]
    missing = sorted({f"{name}: {m}" for name, text in sources for m in COLOUR_CLASS.findall(text) if m not in known})
    assert missing == []


def test_component_classes_are_defined() -> None:
    """A class in a template is either a Tailwind utility or defined in components.css."""
    css = (CSS / "src" / "components.css").read_text(encoding="utf-8")
    defined = set(re.findall(r"\.([a-zA-Z][\w-]*)", css))
    used: set[str] = set()
    for _, text in templates():
        for attr in re.findall(r'(?<![:\w-])class="([^"]*)"', text):
            used.update(c for c in re.sub(r"\{\{.*?\}\}|\{%.*?%\}", " ", attr).split())
        for bound in re.findall(r":class=\"\{([^}]*)\}\"", text):
            used.update(re.findall(r"'([\w-]+)'\s*:", bound))
    used = {c for c in used if not c.endswith("-")}  # completed from data, e.g. attendee-{{ ... }}
    utility = re.compile(r"^(?:m[tblrxy]?|p[tblrxy]?)-\d+$|^text-|^font-|^whitespace-|^cursor-|^block$|^hidden$")
    missing = sorted(c for c in used if c not in defined and not utility.match(c) and c.isascii())
    assert missing == []


def test_attendee_classes_cover_every_status() -> None:
    css = (CSS / "src" / "components.css").read_text(encoding="utf-8")
    for status in ("accepted", "declined", "tentative", "other"):
        assert f".attendee-{status} " in css, status


def test_the_build_output_is_not_committed() -> None:
    assert "app/static/css/app.css" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_templates_have_no_inline_scripts() -> None:
    offenders = [f"{name}: {tag}" for name, text in templates()
                 for tag, body in re.findall(r"(<script\b[^>]*>)(.*?)</script>", text, flags=re.S)
                 if body.strip() or "src=" not in tag]
    assert offenders == []


def test_templates_have_no_inline_event_handlers() -> None:
    offenders = [f"{name}: {m}" for name, text in templates() for m in re.findall(r"\s(on[a-z]+)=[\"']", text)]
    assert offenders == []


def test_scripts_load_before_alpine_starts() -> None:
    base = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    order = [base.find(s) for s in ("{% block content %}", "js/htmx.min.js", "js/app.js", "js/alpine.min.js")]
    assert -1 not in order and order == sorted(order), order
    assert '<script defer src="{{ rp(request) }}/static/js/alpine.min.js"></script>' in base
    for name in ("alpine.min.js", "htmx.min.js"):
        assert (JS / name).stat().st_size > 10_000


def test_components_used_in_templates_are_defined() -> None:
    defined = {m for p in APP_SCRIPTS for m in re.findall(r"Alpine\.data\('(\w+)'", p.read_text(encoding="utf-8"))}
    used = {m for _, text in templates() for m in re.findall(r"x-data=['\"](\w+)[('\"]", text)}
    assert used and used <= defined, used - defined


def test_htmx_toggles_target_their_own_card() -> None:
    macros = (TEMPLATES / "_macros.html").read_text(encoding="utf-8")
    assert 'hx-target="#event-{{ event.id }}" hx-swap="outerHTML"' in macros
    for partial in ("_event_card.html", "_event_detail_card.html"):
        assert 'id="event-{{ event.id }}"' in (TEMPLATES / partial).read_text(encoding="utf-8"), partial
