"""Tests for the pages on the family stack: htmx ticking, the setup page, escaping."""

import html

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Event

HX = {"HX-Request": "true"}


def body(response) -> str:
    """The page as a reader sees it (entities like &#39; decoded)."""
    return html.unescape(response.text)


def test_upcoming_page_renders_cards_with_toggle_forms(client: TestClient, event_with_items: Event):
    page = client.get("/events/upcoming")
    assert page.status_code == 200
    assert f'id="event-{event_with_items.id}"' in page.text
    assert 'name="view" value="card"' in page.text
    assert "(1/3)" in page.text  # one of three items ticked
    assert "cdn.tailwindcss.com" not in page.text


def test_htmx_toggle_returns_the_card(client: TestClient, event_with_items: Event, session: Session):
    item = event_with_items.items[0]
    response = client.post(f"/events/{event_with_items.id}/items/{item.id}/toggle", data={"view": "card"}, headers=HX)
    assert response.status_code == 200
    assert response.text.lstrip().startswith(f'<div class="card event-card') and "<html" not in response.text
    assert f'id="event-{event_with_items.id}"' in response.text
    assert "(2/3)" in response.text
    session.refresh(item)
    assert item.is_checked


def test_htmx_toggle_on_the_detail_page_returns_the_detail_card(client: TestClient, event_with_items: Event):
    for item in event_with_items.items:
        if not item.is_checked:
            client.post(f"/events/{event_with_items.id}/items/{item.id}/toggle", data={"view": "detail"}, headers=HX)
    last = client.post(f"/events/{event_with_items.id}/items/{event_with_items.items[2].id}/toggle",
                       data={"view": "detail"}, headers=HX)
    assert "Push to Google Calendar" in last.text and 'value="detail"' in last.text
    assert "(2/3 complete)" in last.text
    # With every item ticked, Confirm ready is enabled
    again = client.post(f"/events/{event_with_items.id}/items/{event_with_items.items[2].id}/toggle",
                        data={"view": "detail"}, headers=HX)
    assert "(3/3 complete)" in again.text and "Tick every item first" not in again.text


def test_toggle_without_htmx_still_redirects(client: TestClient, event_with_items: Event):
    item = event_with_items.items[0]
    response = client.post(f"/events/{event_with_items.id}/items/{item.id}/toggle", follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"].endswith(f"/events/{event_with_items.id}")


def test_detail_and_archive_pages(client: TestClient, event_with_items: Event):
    page = client.get(f"/events/{event_with_items.id}")
    assert page.status_code == 200 and 'id="event-' in page.text and "Back to upcoming" in body(page)
    assert client.get("/events/archive").status_code == 200


def test_names_are_escaped(client: TestClient, session: Session, event_with_items: Event):
    event_with_items.title = "<b>Party</b> & co"
    session.add(event_with_items)
    session.commit()
    page = client.get(f"/events/{event_with_items.id}")
    assert "&lt;b&gt;Party&lt;/b&gt; &amp; co" in page.text and "<b>Party</b>" not in page.text


def test_setup_page_uses_the_app_layout(client: TestClient):
    page = client.get("/auth/setup")
    assert page.status_code == 200
    assert "/static/css/app.css" in page.text and "cdn.tailwindcss.com" not in page.text
    assert "Setup required" in body(page) or "Credentials already configured" in body(page)
