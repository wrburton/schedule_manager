"""Parse checklist items from event descriptions."""
import re


def parse_items_from_description(description: str | None) -> list[str]:
    """
    Parse checklist items from event description.

    Expected formats:
        Items:
        - Item 1
        - Item 2

    Also supports headers like:
        Checklist:, Things to bring:, Required:, Bring:, Pack:

    And bullet styles: -, *, bullet points, [ ], [x]
    """
    if not description:
        return []

    items = []

    # Pattern to find item sections
    section_pattern = r"(?:Items|Checklist|Things to bring|Required|Bring|Pack):\s*\n"
    matches = list(re.finditer(section_pattern, description, re.IGNORECASE))

    if not matches:
        return []

    for i, match in enumerate(matches):
        start = match.end()
        # End at next section header or end of string
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            # Look for next header-like line (word followed by colon)
            next_header = re.search(r"\n[A-Z][a-z]+:", description[start:])
            if next_header:
                end = start + next_header.start()
            else:
                end = len(description)

        section_text = description[start:end]

        # Parse bullet points: -, *, bullet char, [ ], [x]
        for line in section_text.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Match various bullet styles
            item_match = re.match(
                r"^[-*\u2022]\s+(.+)$"  # - or * or bullet
                r"|^\[[ xX]?\]\s*(.+)$"  # [ ] or [x]
                r"|^(\d+)[.)]\s+(.+)$",  # 1. or 1)
                line,
            )
            if item_match:
                # Get the first non-None group
                item_text = next(
                    (g for g in item_match.groups() if g is not None), None
                )
                if item_text:
                    items.append(item_text.strip())

    return items


def format_items_to_description(
    items: list[str], existing_description: str = ""
) -> str:
    """
    Format items back into description text for pushing to Google Calendar.

    Removes existing Items section and appends new one.
    """
    # Remove existing Items section
    cleaned = re.sub(
        r"Items:\s*\n(?:[-*\u2022]\s+.+\n?)*",
        "",
        existing_description,
        flags=re.IGNORECASE,
    ).strip()

    if not items:
        return cleaned

    items_section = "Items:\n" + "\n".join(f"- {item}" for item in items)

    if cleaned:
        return f"{cleaned}\n\n{items_section}"
    return items_section
