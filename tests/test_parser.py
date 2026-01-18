"""Tests for the description parser."""

from app.calendar.parser import format_items_to_description, parse_items_from_description


class TestParseItemsFromDescription:
    def test_empty_description(self):
        assert parse_items_from_description(None) == []
        assert parse_items_from_description("") == []

    def test_no_items_section(self):
        description = "This is just a regular description without items."
        assert parse_items_from_description(description) == []

    def test_basic_items_section(self):
        description = """Meeting agenda

Items:
- Laptop
- Charger
- Notes
"""
        items = parse_items_from_description(description)
        assert items == ["Laptop", "Charger", "Notes"]

    def test_checklist_header(self):
        description = """Checklist:
- Item 1
- Item 2
"""
        items = parse_items_from_description(description)
        assert items == ["Item 1", "Item 2"]

    def test_things_to_bring_header(self):
        description = """Things to bring:
- Snacks
- Water
"""
        items = parse_items_from_description(description)
        assert items == ["Snacks", "Water"]

    def test_asterisk_bullets(self):
        description = """Items:
* First item
* Second item
"""
        items = parse_items_from_description(description)
        assert items == ["First item", "Second item"]

    def test_checkbox_format(self):
        description = """Items:
[ ] Unchecked item
[x] Checked item
[X] Also checked
"""
        items = parse_items_from_description(description)
        assert items == ["Unchecked item", "Checked item", "Also checked"]

    def test_mixed_content(self):
        description = """Event Description

Some introductory text here.

Items:
- First item
- Second item

Additional notes below the items section.
"""
        items = parse_items_from_description(description)
        assert items == ["First item", "Second item"]

    def test_case_insensitive_header(self):
        description = """ITEMS:
- Item one
- Item two
"""
        items = parse_items_from_description(description)
        assert items == ["Item one", "Item two"]

    def test_whitespace_handling(self):
        description = """Items:
-   Padded item
-Item without space
"""
        items = parse_items_from_description(description)
        assert "Padded item" in items


class TestFormatItemsToDescription:
    def test_empty_items(self):
        result = format_items_to_description([])
        assert result == ""

    def test_empty_items_with_existing(self):
        result = format_items_to_description([], "Existing content")
        assert result == "Existing content"

    def test_basic_formatting(self):
        items = ["Item 1", "Item 2"]
        result = format_items_to_description(items)
        assert result == "Items:\n- Item 1\n- Item 2"

    def test_with_existing_description(self):
        items = ["New item"]
        result = format_items_to_description(items, "Existing content")
        assert "Existing content" in result
        assert "Items:" in result
        assert "- New item" in result

    def test_replaces_existing_items_section(self):
        items = ["New item"]
        existing = """Some text

Items:
- Old item 1
- Old item 2

More text"""
        result = format_items_to_description(items, existing)
        assert "Old item" not in result
        assert "New item" in result
