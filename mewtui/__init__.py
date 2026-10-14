"""A small, explicit terminal UI library for Linux."""

import codecs
import os
import selectors
import termios
import time
from dataclasses import dataclass
from typing import Self

__all__ = ["Char", "Context", "Event", "screen"]


# Colors


# Style


# Geometry


# Events and the input parser


@dataclass(frozen=True, slots=True)
class Char:
    """A typed character, possibly with Ctrl or Alt held."""

    ch: str
    ctrl: bool = False
    alt: bool = False


# Key and Resize join this union in later steps.
Event = Char


def _parse_input(text: str) -> list[Event]:
    """Turn decoded terminal input into events.

    For now only printable characters and Ctrl+letter become events;
    everything else (Enter, Tab, Backspace, ESC and escape sequences) is dropped.
    """
    events: list[Event] = []
    for ch in text:
        code = ord(ch)
        if code == 0x00:
            events.append(Char(" ", ctrl=True))
        elif 0x01 <= code <= 0x1A and ch not in "\t\r":
            events.append(Char(chr(0x60 + code), ctrl=True))
        elif ch.isprintable():
            events.append(Char(ch))
    return events


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


class _Terminal:
    """Owns fds 0 and 1: raw mode, alternate screen, reading and writing bytes."""

    def __init__(self) -> None:
        if not (os.isatty(0) and os.isatty(1)):
            raise RuntimeError("mewtui.screen() needs a terminal on stdin and stdout")
        self._saved = termios.tcgetattr(0)
        self._closed = False
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self._selector = selectors.DefaultSelector()
        self._selector.register(0, selectors.EVENT_READ)
        try:
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
        """Read whatever input is available, or return None after timeout seconds."""
        if not self._selector.select(timeout):
            return None
        return self._decoder.decode(os.read(0, 4096))

    def close(self) -> None:
        """Restore the terminal. Safe to call more than once."""
        if self._closed:
            return
        self._closed = True
        try:
            self.write(_STYLE_RESET + _CURSOR_SHOW + _AUTOWRAP_ON + _ALT_SCREEN_OFF)
        finally:
            termios.tcsetattr(0, termios.TCSAFLUSH, self._saved)
            self._selector.close()


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

    def __enter__(self) -> Self:
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

    def cursor_move(self, x: int, y: int) -> None:
        """Move the cursor to column x, row y (0-based).

        Off-screen positions are allowed; drawing there is cropped.
        """
        self._x = x
        self._y = y
        self._buffer.append(_cup(x, y))

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
        self._buffer.append(_cup(start, self._y))
        self._buffer.append(visible)
        self._x = start + len(visible)

    def flush(self) -> None:
        """Send everything drawn since the last flush to the terminal, in one batch."""
        if not self._buffer:
            return
        self._term().write(_SYNC_BEGIN + "".join(self._buffer) + _SYNC_END)
        self._buffer.clear()

    def wait_event(self, timeout: float | None = None) -> Event | None:
        """Return the next input event.

        timeout=None blocks until one arrives; a number waits at most that many
        seconds and returns None if nothing arrived.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while not self._events:
            remaining = (
                None if deadline is None else max(deadline - time.monotonic(), 0)
            )
            text = self._term().read(remaining)
            if text is None:
                return None
            self._events.extend(_parse_input(text))
        return self._events.pop(0)


def screen() -> Context:
    """Take over the terminal: use as `with mewtui.screen() as ctx:`.

    Entering switches to raw mode and the alternate screen; leaving restores
    everything, also when an exception escapes the block.
    """
    return Context()
