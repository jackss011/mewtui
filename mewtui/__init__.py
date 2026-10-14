"""A small, explicit terminal UI library for Linux."""

import codecs
import os
import re
import selectors
import signal
import termios
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum
from types import FrameType
from typing import Self

__all__ = [
    "Ansi",
    "Char",
    "Color",
    "Context",
    "Event",
    "Indexed",
    "Key",
    "KeyName",
    "Resize",
    "Rgb",
    "Style",
    "default_style",
    "screen",
]


# Colors


@dataclass(frozen=True, slots=True)
class Ansi:
    """One of the 16 theme colors (0-7 normal, 8-15 bright); follows the terminal theme."""

    index: int

    def __post_init__(self) -> None:
        if not 0 <= self.index <= 15:
            raise ValueError(f"Ansi index must be 0-15, got {self.index}")


@dataclass(frozen=True, slots=True)
class Indexed:
    """A color from the terminal's 256-color palette."""

    index: int

    def __post_init__(self) -> None:
        if not 0 <= self.index <= 255:
            raise ValueError(f"Indexed index must be 0-255, got {self.index}")


@dataclass(frozen=True, slots=True)
class Rgb:
    """A 24-bit color."""

    r: int
    g: int
    b: int

    def __post_init__(self) -> None:
        if not all(0 <= c <= 255 for c in (self.r, self.g, self.b)):
            raise ValueError(
                f"Rgb components must be 0-255, got ({self.r}, {self.g}, {self.b})"
            )


Color = Ansi | Indexed | Rgb

# The 148 named colors of CSS Color Level 4 ("transparent" is not a color here).
_CSS_NAMES = {
    "aliceblue": "#f0f8ff",
    "antiquewhite": "#faebd7",
    "aqua": "#00ffff",
    "aquamarine": "#7fffd4",
    "azure": "#f0ffff",
    "beige": "#f5f5dc",
    "bisque": "#ffe4c4",
    "black": "#000000",
    "blanchedalmond": "#ffebcd",
    "blue": "#0000ff",
    "blueviolet": "#8a2be2",
    "brown": "#a52a2a",
    "burlywood": "#deb887",
    "cadetblue": "#5f9ea0",
    "chartreuse": "#7fff00",
    "chocolate": "#d2691e",
    "coral": "#ff7f50",
    "cornflowerblue": "#6495ed",
    "cornsilk": "#fff8dc",
    "crimson": "#dc143c",
    "cyan": "#00ffff",
    "darkblue": "#00008b",
    "darkcyan": "#008b8b",
    "darkgoldenrod": "#b8860b",
    "darkgray": "#a9a9a9",
    "darkgreen": "#006400",
    "darkgrey": "#a9a9a9",
    "darkkhaki": "#bdb76b",
    "darkmagenta": "#8b008b",
    "darkolivegreen": "#556b2f",
    "darkorange": "#ff8c00",
    "darkorchid": "#9932cc",
    "darkred": "#8b0000",
    "darksalmon": "#e9967a",
    "darkseagreen": "#8fbc8f",
    "darkslateblue": "#483d8b",
    "darkslategray": "#2f4f4f",
    "darkslategrey": "#2f4f4f",
    "darkturquoise": "#00ced1",
    "darkviolet": "#9400d3",
    "deeppink": "#ff1493",
    "deepskyblue": "#00bfff",
    "dimgray": "#696969",
    "dimgrey": "#696969",
    "dodgerblue": "#1e90ff",
    "firebrick": "#b22222",
    "floralwhite": "#fffaf0",
    "forestgreen": "#228b22",
    "fuchsia": "#ff00ff",
    "gainsboro": "#dcdcdc",
    "ghostwhite": "#f8f8ff",
    "gold": "#ffd700",
    "goldenrod": "#daa520",
    "gray": "#808080",
    "green": "#008000",
    "greenyellow": "#adff2f",
    "grey": "#808080",
    "honeydew": "#f0fff0",
    "hotpink": "#ff69b4",
    "indianred": "#cd5c5c",
    "indigo": "#4b0082",
    "ivory": "#fffff0",
    "khaki": "#f0e68c",
    "lavender": "#e6e6fa",
    "lavenderblush": "#fff0f5",
    "lawngreen": "#7cfc00",
    "lemonchiffon": "#fffacd",
    "lightblue": "#add8e6",
    "lightcoral": "#f08080",
    "lightcyan": "#e0ffff",
    "lightgoldenrodyellow": "#fafad2",
    "lightgray": "#d3d3d3",
    "lightgreen": "#90ee90",
    "lightgrey": "#d3d3d3",
    "lightpink": "#ffb6c1",
    "lightsalmon": "#ffa07a",
    "lightseagreen": "#20b2aa",
    "lightskyblue": "#87cefa",
    "lightslategray": "#778899",
    "lightslategrey": "#778899",
    "lightsteelblue": "#b0c4de",
    "lightyellow": "#ffffe0",
    "lime": "#00ff00",
    "limegreen": "#32cd32",
    "linen": "#faf0e6",
    "magenta": "#ff00ff",
    "maroon": "#800000",
    "mediumaquamarine": "#66cdaa",
    "mediumblue": "#0000cd",
    "mediumorchid": "#ba55d3",
    "mediumpurple": "#9370db",
    "mediumseagreen": "#3cb371",
    "mediumslateblue": "#7b68ee",
    "mediumspringgreen": "#00fa9a",
    "mediumturquoise": "#48d1cc",
    "mediumvioletred": "#c71585",
    "midnightblue": "#191970",
    "mintcream": "#f5fffa",
    "mistyrose": "#ffe4e1",
    "moccasin": "#ffe4b5",
    "navajowhite": "#ffdead",
    "navy": "#000080",
    "oldlace": "#fdf5e6",
    "olive": "#808000",
    "olivedrab": "#6b8e23",
    "orange": "#ffa500",
    "orangered": "#ff4500",
    "orchid": "#da70d6",
    "palegoldenrod": "#eee8aa",
    "palegreen": "#98fb98",
    "paleturquoise": "#afeeee",
    "palevioletred": "#db7093",
    "papayawhip": "#ffefd5",
    "peachpuff": "#ffdab9",
    "peru": "#cd853f",
    "pink": "#ffc0cb",
    "plum": "#dda0dd",
    "powderblue": "#b0e0e6",
    "purple": "#800080",
    "rebeccapurple": "#663399",
    "red": "#ff0000",
    "rosybrown": "#bc8f8f",
    "royalblue": "#4169e1",
    "saddlebrown": "#8b4513",
    "salmon": "#fa8072",
    "sandybrown": "#f4a460",
    "seagreen": "#2e8b57",
    "seashell": "#fff5ee",
    "sienna": "#a0522d",
    "silver": "#c0c0c0",
    "skyblue": "#87ceeb",
    "slateblue": "#6a5acd",
    "slategray": "#708090",
    "slategrey": "#708090",
    "snow": "#fffafa",
    "springgreen": "#00ff7f",
    "steelblue": "#4682b4",
    "tan": "#d2b48c",
    "teal": "#008080",
    "thistle": "#d8bfd8",
    "tomato": "#ff6347",
    "turquoise": "#40e0d0",
    "violet": "#ee82ee",
    "wheat": "#f5deb3",
    "white": "#ffffff",
    "whitesmoke": "#f5f5f5",
    "yellow": "#ffff00",
    "yellowgreen": "#9acd32",
}

_CSS_HEX3 = re.compile(r"#([0-9a-f])([0-9a-f])([0-9a-f])")
_CSS_HEX6 = re.compile(r"#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})")
_CSS_RGB = re.compile(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")


def _parse_color(value: str | Color) -> Color | None:
    """Turn a color argument into a Color, or None for the terminal default.

    value is "default", a CSS color string, or an Ansi, Indexed or Rgb.
    """
    if not isinstance(value, str):
        return value
    if value.strip().lower() == "default":
        return None
    return _parse_css_color(value)


def _parse_css_color(text: str) -> Rgb:
    """Parse a CSS color: a name, #rgb, #rrggbb or rgb(r, g, b)."""
    css = text.strip().lower()
    css = _CSS_NAMES.get(css, css)
    if match := _CSS_HEX3.fullmatch(css):
        # Each digit is doubled: #f80 is #ff8800.
        r, g, b = (int(digit * 2, 16) for digit in match.groups())
        return Rgb(r, g, b)
    if match := _CSS_HEX6.fullmatch(css):
        r, g, b = (int(pair, 16) for pair in match.groups())
        return Rgb(r, g, b)
    if match := _CSS_RGB.fullmatch(css):
        r, g, b = (int(number) for number in match.groups())
        if not all(0 <= c <= 255 for c in (r, g, b)):
            raise ValueError(f"rgb() components must be 0-255 in {text!r}")
        return Rgb(r, g, b)
    raise ValueError(
        f'not a color: {text!r} (expected "default", a CSS color name, '
        "#rgb, #rrggbb or rgb(r, g, b))"
    )


# Style


@dataclass(frozen=True, slots=True)
class Style:
    """Colors and attributes for drawn text.

    fg and bg of None mean the terminal's default colors.
    """

    fg: Color | None = None
    bg: Color | None = None
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False
    reverse: bool = False
    strikethrough: bool = False


# Set this before screen() to change the style drawing starts with and
# reset_style() returns to.
default_style = Style()


# Geometry


# Events and the input parser


@dataclass(frozen=True, slots=True)
class Char:
    """A typed character, possibly with Ctrl or Alt held."""

    ch: str
    ctrl: bool = False
    alt: bool = False


class KeyName(Enum):
    """The named keys a Key event can carry."""

    UP = "Up"
    DOWN = "Down"
    LEFT = "Left"
    RIGHT = "Right"
    HOME = "Home"
    END = "End"
    PAGE_UP = "PageUp"
    PAGE_DOWN = "PageDown"
    INSERT = "Insert"
    DELETE = "Delete"
    ENTER = "Enter"
    TAB = "Tab"
    BACKSPACE = "Backspace"
    ESCAPE = "Escape"
    F1 = "F1"
    F2 = "F2"
    F3 = "F3"
    F4 = "F4"
    F5 = "F5"
    F6 = "F6"
    F7 = "F7"
    F8 = "F8"
    F9 = "F9"
    F10 = "F10"
    F11 = "F11"
    F12 = "F12"


@dataclass(frozen=True, slots=True)
class Key:
    """A named key such as an arrow or F1, possibly with modifiers."""

    name: KeyName
    ctrl: bool = False
    alt: bool = False
    shift: bool = False


@dataclass(frozen=True, slots=True)
class Resize:
    """The window changed size; width() and height() already report the new size."""

    width: int
    height: int


Event = Char | Key | Resize

# How long to wait after a trailing ESC or partial sequence before deciding.
_ESCAPE_TIMEOUT = 0.03

# Final characters of CSI and SS3 sequences that name a key directly.
_LETTER_KEYS = {
    "A": KeyName.UP,
    "B": KeyName.DOWN,
    "C": KeyName.RIGHT,
    "D": KeyName.LEFT,
    "H": KeyName.HOME,
    "F": KeyName.END,
}

# Keys that only arrive as SS3 (ESC O + one character).
_SS3_KEYS = _LETTER_KEYS | {
    "P": KeyName.F1,
    "Q": KeyName.F2,
    "R": KeyName.F3,
    "S": KeyName.F4,
}

# The number n in CSI n~ (or CSI n;m~).
_TILDE_KEYS = {
    1: KeyName.HOME,
    2: KeyName.INSERT,
    3: KeyName.DELETE,
    4: KeyName.END,
    5: KeyName.PAGE_UP,
    6: KeyName.PAGE_DOWN,
    7: KeyName.HOME,
    8: KeyName.END,
    11: KeyName.F1,
    12: KeyName.F2,
    13: KeyName.F3,
    14: KeyName.F4,
    15: KeyName.F5,
    17: KeyName.F6,
    18: KeyName.F7,
    19: KeyName.F8,
    20: KeyName.F9,
    21: KeyName.F10,
    23: KeyName.F11,
    24: KeyName.F12,
}


def _parse_input(text: str) -> tuple[list[Event], str]:
    """Turn decoded terminal input into events.

    Returns the events and any unfinished escape sequence at the end of text.
    The caller keeps that leftover, prepends it to the next input, or passes it
    to _parse_leftover() if no more input arrives in time.
    """
    events: list[Event] = []
    i = 0
    while i < len(text):
        if text[i] == "\x1b":
            result = _parse_escape(text, i)
            if result is None:
                return events, text[i:]
            event, i = result
        else:
            event = _char_event(text[i])
            i += 1
        if event is not None:
            events.append(event)
    return events, ""


def _parse_leftover(leftover: str) -> list[Event]:
    """Decide what an unfinished sequence meant once no more input came."""
    if leftover == "\x1b":
        return [Key(KeyName.ESCAPE)]
    return []


def _char_event(ch: str) -> Event | None:
    """The event for one character outside an escape sequence, if any."""
    code = ord(ch)
    if ch == "\r":
        return Key(KeyName.ENTER)
    if ch == "\t":
        return Key(KeyName.TAB)
    if ch == "\x7f":
        return Key(KeyName.BACKSPACE)
    if ch == "\x1b":
        return Key(KeyName.ESCAPE)
    if code == 0x00:
        return Char(" ", ctrl=True)
    if 0x01 <= code <= 0x1A:
        return Char(chr(0x60 + code), ctrl=True)
    if ch.isprintable():
        return Char(ch)
    return None


def _parse_escape(text: str, i: int) -> tuple[Event | None, int] | None:
    """Parse the sequence starting with the ESC at text[i].

    Returns the event (None if dropped) and the index after the sequence,
    or None if text ends before the sequence is complete.
    """
    if i + 1 == len(text):
        return None
    second = text[i + 1]
    if second == "[":
        return _parse_csi(text, i + 2)
    if second == "O":
        if i + 2 == len(text):
            return None
        name = _SS3_KEYS.get(text[i + 2])
        return (Key(name) if name else None), i + 3
    event = _char_event(second)
    return (replace(event, alt=True) if event else None), i + 2


def _parse_csi(text: str, start: int) -> tuple[Event | None, int] | None:
    """Parse a CSI sequence whose parameters begin at text[start].

    A CSI is parameter bytes 0x30-0x3F, intermediate bytes 0x20-0x2F, then one
    final byte 0x40-0x7E. Returns None if text ends before the final byte.
    """
    i = start
    while i < len(text) and "\x30" <= text[i] <= "\x3f":
        i += 1
    params_end = i
    while i < len(text) and "\x20" <= text[i] <= "\x2f":
        i += 1
    if i == len(text):
        return None
    final = text[i]
    if not "\x40" <= final <= "\x7e":
        # Malformed: drop what was read and resume at the offending character.
        return None, i
    if params_end != i:
        # Intermediate bytes: no key uses them.
        return None, i + 1
    return _csi_event(text[start:params_end], final), i + 1


def _csi_event(params: str, final: str) -> Key | None:
    """The key for a CSI sequence with the given parameters and final byte."""
    fields = params.split(";") if params else []
    if not all(field.isdigit() for field in fields) or len(fields) > 2:
        return None
    numbers = [int(field) for field in fields]
    modifier = numbers[1] if len(numbers) == 2 else 1
    if final == "~":
        if not numbers or numbers[0] not in _TILDE_KEYS:
            return None
        return _with_modifier(_TILDE_KEYS[numbers[0]], modifier)
    if final == "Z" and not numbers:
        return Key(KeyName.TAB, shift=True)
    if final in _LETTER_KEYS and numbers in ([], [1], [1, modifier]):
        return _with_modifier(_LETTER_KEYS[final], modifier)
    return None


def _with_modifier(name: KeyName, modifier: int) -> Key | None:
    """Build a Key from a modifier parameter: modifier - 1 is a bitmask.

    The bits are 1 = shift, 2 = alt, 4 = ctrl; anything below 1 is invalid.
    """
    if modifier < 1:
        return None
    bits = modifier - 1
    return Key(name, ctrl=bool(bits & 4), alt=bool(bits & 2), shift=bool(bits & 1))


# Escape sequences

# Alternate screen on / off (the 1049 variant also saves and restores the cursor).
_ALT_SCREEN_ON = "\x1b[?1049h"
_ALT_SCREEN_OFF = "\x1b[?1049l"

# DECAWM: auto-wrap on / off.
_AUTOWRAP_ON = "\x1b[?7h"
_AUTOWRAP_OFF = "\x1b[?7l"

# DECTCEM: show / hide the cursor.
_CURSOR_SHOW = "\x1b[?25h"
_CURSOR_HIDE = "\x1b[?25l"

# SGR 0: reset all style attributes.
_STYLE_RESET = "\x1b[0m"

# Synchronized output: the terminal paints everything in between at once.
_SYNC_BEGIN = "\x1b[?2026h"
_SYNC_END = "\x1b[?2026l"


# ED 2: erase the whole window, filling it with the current background color.
_ERASE_SCREEN = "\x1b[2J"


def _sgr(style: Style) -> str:
    """SGR: set the full style, starting from a reset (0) so nothing carries over.

    Example: bold red text on the default background is \x1b[0;1;38;2;255;0;0m.
    """
    params = ["0"]
    for on, code in [
        (style.bold, "1"),
        (style.dim, "2"),
        (style.italic, "3"),
        (style.underline, "4"),
        (style.reverse, "7"),
        (style.strikethrough, "9"),
    ]:
        if on:
            params.append(code)
    if style.fg is not None:
        params.append(_color_params(style.fg, background=False))
    if style.bg is not None:
        params.append(_color_params(style.bg, background=True))
    return f"\x1b[{';'.join(params)}m"


def _color_params(color: Color, background: bool) -> str:
    """The SGR parameters that select color as foreground or background."""
    match color:
        case Ansi(index) if index < 8:
            return str((40 if background else 30) + index)
        case Ansi(index):
            return str((100 if background else 90) + index - 8)
        case Indexed(index):
            return f"{48 if background else 38};5;{index}"
        case Rgb(r, g, b):
            return f"{48 if background else 38};2;{r};{g};{b}"


def _cup(x: int, y: int) -> str:
    """CUP: move cursor to (row, col), 1-based.

    The tracked cursor may be off-screen; CUP needs positive numbers, so negative
    positions are raised to 1 (the terminal itself clamps the far edges).
    """
    return f"\x1b[{max(y + 1, 1)};{max(x + 1, 1)}H"


def _sanitize(text: str) -> str:
    """Replace control characters (C0, DEL, C1) with U+FFFD."""
    return "".join("�" if _is_control(ch) else ch for ch in text)


def _is_control(ch: str) -> bool:
    code = ord(ch)
    return code < 0x20 or 0x7F <= code <= 0x9F


def _crop_line(text: str, x: int, width: int) -> tuple[int, str]:
    """Return the start column and the part of text that is visible.

    text is drawn starting at column x of a window `width` columns wide.
    """
    start = max(x, 0)
    visible = text[start - x : width - x]
    return start, visible


# Terminal


# What signal.signal() returns: a handler, SIG_DFL/SIG_IGN, or None.
_SignalHandler = Callable[[int, FrameType | None], object] | int | None


class _Terminal:
    """Owns fds 0 and 1: raw mode, alternate screen, reading and writing bytes.

    It also turns SIGWINCH into something select() can wait on: the signal's
    wakeup fd writes the signal number into a pipe whose read end is selected
    together with fd 0.
    """

    def __init__(self) -> None:
        if not (os.isatty(0) and os.isatty(1)):
            raise RuntimeError("mewtui.screen() needs a terminal on stdin and stdout")
        self._saved = termios.tcgetattr(0)
        self._closed = False
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self._signal_r, self._signal_w = os.pipe()
        os.set_blocking(self._signal_r, False)
        os.set_blocking(self._signal_w, False)
        self._selector = selectors.DefaultSelector()
        self._selector.register(0, selectors.EVENT_READ)
        self._selector.register(self._signal_r, selectors.EVENT_READ)
        self._old_handler: _SignalHandler = None
        self._old_wakeup_fd = -1
        self._signals_set = False
        try:
            self._old_handler = signal.signal(signal.SIGWINCH, _on_sigwinch)
            self._old_wakeup_fd = signal.set_wakeup_fd(self._signal_w)
            self._signals_set = True
            self._enter_raw_mode()
            self.write(_ALT_SCREEN_ON + _AUTOWRAP_OFF)
        except BaseException:
            self.close()
            raise

    def _enter_raw_mode(self) -> None:
        raw = list(self._saved)
        raw[6] = list(self._saved[6])  # cc is a nested list; copy it too
        raw[0] &= ~(
            termios.BRKINT
            | termios.ICRNL
            | termios.INPCK
            | termios.ISTRIP
            | termios.IXON
        )
        raw[1] &= ~termios.OPOST
        raw[2] |= termios.CS8
        raw[3] &= ~(termios.ECHO | termios.ICANON | termios.ISIG | termios.IEXTEN)
        raw[6][termios.VMIN] = 1
        raw[6][termios.VTIME] = 0
        termios.tcsetattr(0, termios.TCSAFLUSH, raw)

    def size(self) -> tuple[int, int]:
        """Return (width, height) as the terminal reports it now."""
        columns, lines = os.get_terminal_size(1)
        return columns, lines

    def write(self, text: str) -> None:
        """Write text to fd 1 right away, looping until every byte is out."""
        data = text.encode("utf-8")
        while data:
            written = os.write(1, data)
            data = data[written:]

    def read(self, timeout: float | None) -> str | None:
        """Wait for input or a resize, and read whatever input is available.

        Returns None after timeout seconds with nothing ready, and "" when only
        the signal pipe is ready (see take_resize()).
        """
        ready = self._selector.select(timeout)
        if not ready:
            return None
        if not any(key.fd == 0 for key, _ in ready):
            return ""
        return self._decoder.decode(os.read(0, 4096))

    def take_resize(self) -> bool:
        """Drain the signal pipe without blocking; True if SIGWINCH arrived."""
        resized = False
        while True:
            try:
                data = os.read(self._signal_r, 4096)
            except BlockingIOError:
                return resized
            # Other signals with Python handlers write their numbers here too.
            resized = resized or signal.SIGWINCH in data

    def close(self) -> None:
        """Restore the terminal. Safe to call more than once."""
        if self._closed:
            return
        self._closed = True
        try:
            self.write(_STYLE_RESET + _CURSOR_SHOW + _AUTOWRAP_ON + _ALT_SCREEN_OFF)
        finally:
            termios.tcsetattr(0, termios.TCSAFLUSH, self._saved)
            self._restore_signals()

    def _restore_signals(self) -> None:
        if self._signals_set:
            signal.set_wakeup_fd(self._old_wakeup_fd)
            # None means the old handler was not set from Python: use the default.
            old = signal.SIG_DFL if self._old_handler is None else self._old_handler
            signal.signal(signal.SIGWINCH, old)
        self._selector.close()
        os.close(self._signal_r)
        os.close(self._signal_w)


def _on_sigwinch(signum: int, frame: FrameType | None) -> None:
    """Do nothing: the wakeup fd already recorded the signal for select()."""


# Context and screen()


class Context:
    """Drawing and input for one screen() session.

    All drawing goes into a buffer; nothing reaches the terminal until flush().
    """

    def __init__(self) -> None:
        self._terminal: _Terminal | None = None
        self._width = 0
        self._height = 0
        self._x = 0
        self._y = 0
        self._buffer: list[str] = []
        self._events: list[Event] = []
        self._leftover = ""
        self._default_style = default_style
        self._style = default_style
        # What the terminal has; None until the first SGR, so the first draw emits one.
        self._emitted_style: Style | None = None

    def __enter__(self) -> Self:
        # Read the global now, so setting it any time before screen() works.
        self._default_style = default_style
        self._style = default_style
        self._terminal = _Terminal()
        self._width, self._height = self._terminal.size()
        return self

    def __exit__(self, *exc_info: object) -> None:
        # Unflushed drawing is discarded, not written.
        self._buffer.clear()
        if self._terminal is not None:
            self._terminal.close()

    def _term(self) -> _Terminal:
        if self._terminal is None:
            raise RuntimeError("use the Context inside 'with mewtui.screen() as ctx:'")
        return self._terminal

    def width(self) -> int:
        """Window width in columns, as of the last event the program saw."""
        return self._width

    def height(self) -> int:
        """Window height in rows, as of the last event the program saw."""
        return self._height

    def size(self) -> tuple[int, int]:
        """Return (width, height)."""
        return self._width, self._height

    def cursor_set(self, x: int, y: int) -> None:
        """Move the cursor to column x, row y (0-based).

        Off-screen positions are allowed; drawing there is cropped.
        """
        self._x = x
        self._y = y
        self._buffer.append(_cup(x, y))

    def cursor_delta(self, dx: int, dy: int) -> None:
        """Move the cursor by dx columns and dy rows from where it is.

        Same rules as cursor_set(): the result may be off-screen.
        """
        self.cursor_set(self._x + dx, self._y + dy)

    def cursor_visibility(self, visible: bool) -> None:
        """Show or hide the cursor."""
        self._buffer.append(_CURSOR_SHOW if visible else _CURSOR_HIDE)

    def put(self, text: str) -> None:
        """Write the first line of text at the cursor, cropped to the window.

        Control characters become U+FFFD. The cursor ends right after the last
        character written, but never past column width(). If nothing is visible,
        nothing is written and the cursor stays where it was.
        """
        line = _sanitize(text.split("\n", 1)[0])
        if not 0 <= self._y < self._height:
            return
        start, visible = _crop_line(line, self._x, self._width)
        if not visible:
            return
        self._emit_style()
        self._buffer.append(_cup(start, self._y))
        self._buffer.append(visible)
        self._x = start + len(visible)

    def set(self, char: str, x: int, y: int) -> None:
        """Draw one character at column x, row y, without moving the cursor.

        Uses the current style. Off-screen cells are dropped, a control character
        becomes U+FFFD, and anything but exactly one character raises ValueError.
        """
        if len(char) != 1:
            raise ValueError(f"set() needs exactly one character, got {char!r}")
        if not (0 <= x < self._width and 0 <= y < self._height):
            return
        self._emit_style()
        self._buffer.append(_cup(x, y))
        self._buffer.append(_sanitize(char))
        # Put the terminal's cursor back where the program's cursor is.
        self._buffer.append(_cup(self._x, self._y))

    def style(
        self,
        fg: str | Color | None = None,
        bg: str | Color | None = None,
        bold: bool | None = None,
        dim: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
        reverse: bool | None = None,
        strikethrough: bool | None = None,
    ) -> None:
        """Change the style for what is drawn next.

        Only the arguments given change; None keeps the current value. A color is
        "default" (the terminal's), a CSS color string, or an Ansi, Indexed or Rgb.
        Raises ValueError for a malformed color.
        """
        old = self._style
        self._style = Style(
            fg=old.fg if fg is None else _parse_color(fg),
            bg=old.bg if bg is None else _parse_color(bg),
            bold=old.bold if bold is None else bold,
            dim=old.dim if dim is None else dim,
            italic=old.italic if italic is None else italic,
            underline=old.underline if underline is None else underline,
            reverse=old.reverse if reverse is None else reverse,
            strikethrough=old.strikethrough if strikethrough is None else strikethrough,
        )

    def reset_style(self) -> None:
        """Go back to the default style (mewtui.default_style when screen() started)."""
        self._style = self._default_style

    def clear(self) -> None:
        """Erase the whole window with the current background color.

        The cursor stays where it was.
        """
        self._emit_style()
        self._buffer.append(_ERASE_SCREEN)

    def _emit_style(self) -> None:
        """Append an SGR if the terminal's style differs from the current one."""
        if self._emitted_style != self._style:
            self._buffer.append(_sgr(self._style))
            self._emitted_style = self._style

    def flush(self) -> None:
        """Send everything drawn since the last flush to the terminal, in one batch."""
        if not self._buffer:
            return
        self._term().write(_SYNC_BEGIN + "".join(self._buffer) + _SYNC_END)
        self._buffer.clear()

    def wait_event(self, timeout: float | None = None) -> Event | None:
        """Return the next input event.

        timeout=None blocks until one arrives; a number waits at most that many
        seconds and returns None if nothing arrived. A window resize is checked
        first on every call: if the size changed, it is stored and a Resize is
        returned ahead of any queued key events.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            # A SIGWINCH can arrive twice for one resize (`uv run` forwards it),
            # so only a real change of size becomes an event.
            if self._term().take_resize() and self._term().size() != self.size():
                self._width, self._height = self._term().size()
                return Resize(self._width, self._height)
            if self._events:
                return self._events.pop(0)
            if self._leftover:
                # A trailing ESC may be the start of a sequence: give the rest
                # of it a moment to arrive before deciding.
                text = self._term().read(_ESCAPE_TIMEOUT)
                if text is None:
                    self._events.extend(_parse_leftover(self._leftover))
                    self._leftover = ""
                    continue
            else:
                remaining = (
                    None if deadline is None else max(deadline - time.monotonic(), 0)
                )
                text = self._term().read(remaining)
                if text is None:
                    return None
            events, self._leftover = _parse_input(self._leftover + text)
            self._events.extend(events)


def screen() -> Context:
    """Take over the terminal: use as `with mewtui.screen() as ctx:`.

    Entering switches to raw mode and the alternate screen; leaving restores
    everything, also when an exception escapes the block.
    """
    return Context()
