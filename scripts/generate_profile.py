# Copyright © 2026 NLSystems | Sóley.
# All rights reserved.
#
# View-only for inspection, review, debugging, and analysis.
#
# Public visibility does not grant permission to copy, reuse,
# redistribute, republish, modify, create derivative works from,
# or incorporate this source into another project.
#
# AI and automated tools may inspect and analyze this source when
# explicitly requested by a user. This does not grant permission to
# reproduce substantially identical copies, redistribute the work,
# or use it for model training or fine-tuning.
#
# See LICENSE for full terms.

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from calendar import monthrange
from base64 import b64encode
import re


ROOT = Path(__file__).resolve().parents[1]

DARK_FILE = ROOT / "dark_mode.svg"
LIGHT_FILE = ROOT / "light_mode.svg"
ASSET = ROOT / "assets" / "soley.png"

# Iceland = UTC all year.
BIRTHDAY = datetime(
    1999,
    9,
    15,
    15,
    3,
    tzinfo=timezone.utc,
)

TZ = timezone.utc


def plural(value: int, unit: str) -> str:
    return f"{value} {unit}" + ("" if value == 1 else "s")


def age_parts(
    now: datetime,
    birth: datetime,
) -> tuple[int, int, int]:
    years = now.year - birth.year
    months = now.month - birth.month
    days = now.day - birth.day

    if days < 0:
        prev_year = now.year
        prev_month = now.month - 1

        if prev_month == 0:
            prev_month = 12
            prev_year -= 1

        days += monthrange(prev_year, prev_month)[1]
        months -= 1

    if months < 0:
        months += 12
        years -= 1

    return years, months, days


def uptime_string(now: datetime) -> str:
    years, months, days = age_parts(now, BIRTHDAY)

    return (
        f"{plural(years, 'year')}, "
        f"{plural(months, 'month')}, "
        f"{plural(days, 'day')}"
    )


def is_birthday(now: datetime) -> bool:
    return (
        now.month == BIRTHDAY.month
        and now.day == BIRTHDAY.day
    )


def image_data_uri(path: Path) -> str:
    encoded = b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def validate_svg(path: Path, svg: str) -> None:
    """
    Protect the intentional Dark/Light theme differences.
    This does NOT modify anything.
    """

    if path.name == "dark_mode.svg":
        required = [
            ".small {",
            "fill: #ecedf2;",
            'class="small" text-anchor="end">SYSTEMS',
        ]

    elif path.name == "light_mode.svg":
        required = [
            ".small {",
            ".small2 {",
            'class="small2" text-anchor="end">SYSTEMS',
            'class="small2" text-anchor="end">PEOPLE',
            'class="small2" text-anchor="end">PROGRESS',
        ]

    else:
        raise RuntimeError(f"Unexpected SVG file: {path.name}")

    for marker in required:
        if marker not in svg:
            raise RuntimeError(
                f"{path.name}: expected design marker missing: {marker}"
            )


def update_photo(svg: str) -> str:
    """
    Replace only the embedded PNG data.
    Position, crop, width, height and clip-path stay untouched.
    """

    if not ASSET.exists():
        return svg

    photo = image_data_uri(ASSET)

    pattern = (
        r'(<image\s+href=")'
        r'data:image/png;base64,[^"]+'
        r'(")'
    )

    updated, count = re.subn(
        pattern,
        lambda match: (
            f'{match.group(1)}{photo}{match.group(2)}'
        ),
        svg,
        count=1,
    )

    if count != 1:
        raise RuntimeError(
            "Could not find exactly one embedded profile image."
        )

    return updated


def update_uptime(
    svg: str,
    now: datetime,
) -> str:
    """
    Update the Uptime row and dynamically adjust its dot leader.

    The intended row width is derived from the surrounding monospaced
    profile rows instead of preserving the previous Uptime width.
    """

    uptime = uptime_string(now)

    row_pattern = re.compile(
        r'<text'
        r'[^>]*'
        r'class="(?:mono|mono accentline)"'
        r'[^>]*>'
        r'([^<]+)'
        r'</text>'
    )

    row_lengths = []

    for match in row_pattern.finditer(svg):
        row_text = match.group(1)

        if (
            "." in row_text
            and not row_text.startswith("Uptime")
        ):
            row_lengths.append(len(row_text))

    if not row_lengths:
        raise RuntimeError(
            "Could not determine profile row width."
        )

    # Use the most common width of the other profile rows.
    target_width = max(
        set(row_lengths),
        key=row_lengths.count,
    )

    pattern = (
        r'(<text'
        r'[^>]*'
        r'class="(?:mono|mono accentline)"'
        r'[^>]*>)'
        r'(Uptime\s+)'
        r'(\.+)'
        r'(\s+)'
        r'(\d+\s+years?,\s+'
        r'\d+\s+months?,\s+'
        r'\d+\s+days?)'
        r'(</text>)'
    )

    def replacement(match: re.Match[str]) -> str:
        label = match.group(2)
        separator = match.group(4)

        dot_count = max(
            2,
            target_width
            - len(label)
            - len(separator)
            - len(uptime),
        )

        dots = "." * dot_count

        return (
            f"{match.group(1)}"
            f"{label}"
            f"{dots}"
            f"{separator}"
            f"{uptime}"
            f"{match.group(6)}"
        )

    updated, count = re.subn(
        pattern,
        replacement,
        svg,
        count=1,
    )

    if count != 1:
        raise RuntimeError(
            "Could not find exactly one Uptime row."
        )

    return updated


def update_birthday_class(
    svg: str,
    now: datetime,
) -> str:
    """
    On September 15 the existing Uptime row becomes accent-colored.

    On every other day it uses the normal mono class.

    Nothing else is changed.
    """

    if is_birthday(now):
        pattern = (
            r'(<text'
            r'[^>]*'
            r')class="mono"'
            r'([^>]*>'
            r'Uptime\s+\.)'
        )

        replacement = (
            r'\1class="mono accentline"\2'
        )

    else:
        pattern = (
            r'(<text'
            r'[^>]*'
            r')class="mono accentline"'
            r'([^>]*>'
            r'Uptime\s+\.)'
        )

        replacement = (
            r'\1class="mono"\2'
        )

    return re.sub(
        pattern,
        replacement,
        svg,
        count=1,
    )


def update_svg(
    path: Path,
    now: datetime,
) -> None:
    svg = path.read_text(
        encoding="utf-8",
    )

    # Validate your intentional design first.
    validate_svg(
        path,
        svg,
    )

    # Only dynamic content below.
    svg = update_photo(svg)

    svg = update_uptime(
        svg,
        now,
    )

    svg = update_birthday_class(
        svg,
        now,
    )

    path.write_text(
        svg,
        encoding="utf-8",
        newline="\n",
    )

    print(
        f"Updated {path.name}: "
        f"{uptime_string(now)}"
    )


def main() -> None:
    now = datetime.now(TZ)

    update_svg(
        DARK_FILE,
        now,
    )

    update_svg(
        LIGHT_FILE,
        now,
    )

    print(
        "Profile updated without rebuilding "
        "or restyling the SVGs."
    )


if __name__ == "__main__":
    main()