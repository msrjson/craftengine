"""Craft Engine wordmark and brand palette.

Single source for the mark shown when the framework starts: the console
banner printed by `serve`, and the starter page a freshly generated project
answers `/` with. Both read from here so the two can never drift apart.

This module holds no markup. The wordmark is plain text and the palette is a
set of hex strings; turning either into HTML is the view layer's job.
"""

from typing import Final

# The brand palette, carried over from the theme that shipped with the demo
# application. The theme itself is gone from the skeleton; these six values
# are the part worth keeping, because they identify the product rather than
# decorate a page.
BRAND_ORANGE: Final[str] = "#f97316"
BRAND_ORANGE_DARK: Final[str] = "#ea580c"
BRAND_ORANGE_LIGHT: Final[str] = "#fb923c"
SLATE_900: Final[str] = "#0f172a"
SLATE_800: Final[str] = "#1e293b"
SLATE_400: Final[str] = "#94a3b8"

#: The product name drawn in block characters, on a single row, because the
#: mark is one word. Eighty-eight columns wide: past the eighty-column
#: convention, so callers that render into a terminal should expect wrapping
#: on a narrow one. The page scales it to the viewport instead.
WORDMARK: Final[str] = r"""
 ██████ ██████   █████  ███████ ████████ ███████ ███    ██  ██████  ██ ███    ██ ███████
██      ██   ██ ██   ██ ██         ██    ██      ████   ██ ██       ██ ████   ██ ██
██      ██████  ███████ █████      ██    █████   ██ ██  ██ ██   ███ ██ ██ ██  ██ █████
██      ██   ██ ██   ██ ██         ██    ██      ██  ██ ██ ██    ██ ██ ██  ██ ██ ██
 ██████ ██   ██ ██   ██ ██         ██    ███████ ██   ████  ██████  ██ ██   ████ ███████
"""

_RESET: Final[str] = "\033[0m"


def _truecolor(hex_color: str) -> str:
    """Return the ANSI escape that sets the foreground to a hex color.

    Args:
        hex_color: A color in `#rrggbb` form.

    Returns:
        The SGR escape sequence selecting that color as the foreground.
    """
    red = int(hex_color[1:3], 16)
    green = int(hex_color[3:5], 16)
    blue = int(hex_color[5:7], 16)
    return f"\033[38;2;{red};{green};{blue}m"


def console_banner(version: str, release: str) -> str:
    """Return the startup banner for terminal output.

    Args:
        version: The semantic version, such as `3.23.0`.
        release: The monotonic release counter, such as `r00017`.

    Returns:
        The wordmark in brand orange with a dimmed version line, wrapped in
        ANSI escapes. Terminals that do not support truecolor degrade to the
        nearest color rather than printing the escapes.
    """
    orange = _truecolor(BRAND_ORANGE)
    dim = _truecolor(SLATE_400)
    mark = f"{orange}{WORDMARK.strip(chr(10))}{_RESET}"
    stamp = f"{dim}   {version} {release}{_RESET}"
    return f"\n{mark}\n\n{stamp}\n"
