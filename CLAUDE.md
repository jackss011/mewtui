# mewtui

A small Python TUI library built from scratch (not a port of another framework), for internal use at the user's company. The long-term goal is an immediate-mode TUI; v0 is a thin, explicit layer over the terminal: raw mode, cursor, styles, buffered output, and input events.

## Working agreement

- The user wants control over the implementation. Keep the library simple, propose small pieces, and don't scaffold or add features beyond what is asked.
- Examples drive development: each example in `examples/` justifies the next piece of the library.
- Design questions get settled with the user when they come up, not decided up front. Ask before adding any public function, class or parameter that is not in the spec below.
- Work in small, reviewable steps. After each step, say what changed and what the next step would be.

## Scope

- Linux only for now (termios, tty, selectors, SIGWINCH). No Windows code paths, no curses.
- Internal project: never publish to PyPI. Colleagues install it from the company git server (`uv add git+https://…/mewtui`).

## Layout

The whole library lives in **one file**: `mewtui/__init__.py`. Do not split it into modules, even as it grows. Use section comments to organize it instead (see Coding style).

```
mewtui/                 repo root
├── CLAUDE.md
├── pyproject.toml
├── mewtui/
│   └── __init__.py     the entire library
├── examples/           numbered, standalone examples
│   ├── 01_hello.py
│   └── 02_keys.py
└── tests/
    └── test_*.py
```

## Setup

- Python: 3.11 or newer (`requires-python = ">=3.11"`; still to be confirmed, see open questions).
- Use uv for everything: environment, dependencies, running, building.
- Create `pyproject.toml` with `uv init --lib --build-backend uv`, keeping the `[build-system]` block it generates, then adapt it:
  - `name = "mewtui"`, `dependencies = []`.
  - Flat layout (no `src/`): add
    ```toml
    [tool.uv.build-backend]
    module-root = ""
    ```
  - Delete anything `uv init` generated that isn't used (e.g. a `src/` folder, `py.typed` stays if useful).
- Everyday commands, all from the repo root:
  - `uv sync`: create the venv and install mewtui in editable mode.
  - `uv run examples/01_hello.py`: run an example.
  - `uv run pytest`: run tests.
  - `uv run ruff format` and `uv run ruff check`: format and lint.

## Dependencies

- **Runtime: none.** The library uses only the standard library. Expected modules: `os`, `sys`, `termios`, `tty`, `selectors`, `signal`, `atexit`, `codecs`, `re`, `dataclasses`, `enum`, `typing`, `unicodedata`.
- **Dev only**, in the `dev` dependency group (`uv add --dev pytest ruff`): `pytest` for tests, `ruff` for formatting and linting.
- Do not add any other dependency, runtime or dev, without asking the user first.

## Coding style

**File organization.** `mewtui/__init__.py` is ordered top-down with a comment header per section:

1. Colors (`Ansi`, `Indexed`, `Rgb`, CSS parsing)
2. Style (`Style`, `default_style`)
3. Geometry (`Box`)
4. Events (`Char`, `Key`, `Resize`) and the input parser
5. Escape sequences (small functions or constants that build them)
6. Terminal (raw mode, alternate screen, reading and writing bytes)
7. `Context` and `screen()`

Public names are listed in `__all__`. Everything else starts with an underscore.

**Types and data.**
- Type hints on every function and attribute. Use 3.11 syntax: `X | Y`, `list[int]`, no `Optional` or `Union`.
- Value types are `@dataclass(frozen=True, slots=True)`.
- Tagged unions are a type alias over those dataclasses (`Color = Ansi | Indexed | Rgb`, `Event = Char | Key | Resize`) and are consumed with `match`, not `isinstance` chains.
- Plain `Enum` for closed sets of names (e.g. the key names).

**Clarity over cleverness.**
- No metaclasses, decorators that hide control flow, or dynamic attribute tricks.
- Small functions with one job. Prefer a few explicit lines over a compact trick.
- Every escape sequence gets a comment naming it and what it does, e.g. `# CUP: move cursor to (row, col), 1-based`.
- Comments explain *why*; the code shows *what*.
- Short docstrings on public functions and classes: one line, plus a sentence or two on non-obvious behavior (cropping, inheritance, timeouts).

**Behavior rules.**
- The library never prints or logs. All output goes through the context's buffer and reaches the terminal only in `flush()`.
- The buffer accumulates `str`; `flush()` encodes to UTF-8 and writes with `os.write`, looping until every byte is written.
- Terminal restore (termios settings, alternate screen, cursor visibility, style) lives in `__exit__` / `finally`, runs on exceptions too, and is safe to call twice.
- Invalid input from the caller (a malformed CSS color, an out-of-range palette index) raises `ValueError` with a clear message. Drawing outside the window is not an error: it is cropped, as specified.
- Formatting and lint: ruff defaults. Code must pass `uv run ruff format --check` and `uv run ruff check`.

**Debugging tip.** While the terminal is in raw mode on the alternate screen, `print()` is invisible or garbles the display. Write debug output to a file instead (e.g. `open("debug.log", "a")`), and never leave it in committed code.

## Tests

- Test the pure parts without a terminal: CSS color parsing, SGR generation from a `Style`, `put` cropping and wrapping, and the input parser (bytes in, events out).
- Keep terminal-dependent code thin so it rarely needs testing; it is exercised by the examples.
- Tests live in `tests/test_*.py` and run with `uv run pytest`.

## Examples

- Numbered and standalone: `01_hello.py`, `02_keys.py`, and so on. Each shows one thing.
- Short: an example is something to read, not an app.
- Each example decides how to quit (e.g. on `q` or Ctrl-C) and says so on screen.
- Run with `uv run examples/<name>.py`; no path hacks or `sys.path` edits.

## v0 interface

```python
import mewtui
from mewtui import Style, Box, Ansi, Indexed, Rgb

mewtui.default_style = Style(...)        # optional, set before screen()

with mewtui.screen() as ctx:             # raw mode + alternate screen, restored on exit
    ctx.width(); ctx.height(); ctx.size()    # size() -> (width, height)
    ctx.cursor_move(x, y)                     # 0-based column, row
    ctx.cursor_visibility(visible)
    ctx.style(fg=None, bg=None, bold=None, dim=None, italic=None,
              underline=None, reverse=None, strikethrough=None)
    ctx.reset_style()
    ctx.put(text, wrap=False)
    ctx.clear(box=None)
    ctx.flush()
    event = ctx.wait_event(timeout=None)
```

### Decisions

- **`screen()`**: enters raw mode and the alternate screen; on exit (including exceptions) restores everything. It does not touch cursor visibility on enter; that is left to `cursor_visibility`.
- **Coordinates**: 0-based `(x, y)` = (column, row). Converted to the terminal's 1-based form internally.
- **Output is buffered**: all calls append to an internal buffer. Bytes reach the terminal only when `flush()` is called. No automatic flushing.
- **Style inherits**: `style(...)` only changes the arguments that are given; `None` means keep the current value. `reset_style()` returns to the default style.
- **Default style**: a global `mewtui.default_style` (a `Style` struct) the user can set before `screen()`, with nice defaults.
- **Colors**: a color argument is one of
  - the string `"default"` (terminal default),
  - a CSS color string: named colors, `#rgb`, `#rrggbb`, `rgb(r, g, b)`; these always become `Rgb`,
  - a terminal color built directly: `Ansi(0-15)` (follows the terminal theme), `Indexed(0-255)`, `Rgb(r, g, b)`.
  Internally this is a tagged union (frozen dataclasses) mapping to SGR sequences.
- **Attributes**: bold, dim, italic, underline, reverse, strikethrough.
- **`put(text, wrap=False)`**: by default writes only the first line of `text`, cropped to the window width. With `wrap=True` it breaks on `\n` and at the right edge, continuing at the column where the `put` started. Text past the bottom edge is dropped. No scrolling.
- **Cursor after `put`**: right after the last character written, in both modes, but never past column `width` (the column just past the last visible one), so a further `put` on that row is cropped to nothing. With `wrap=True`, a line that ends exactly at the right edge leaves the cursor at the edge rather than on the next row, and when lines are dropped past the bottom the cursor stays after the last character actually written. `cursor_move` can still place the cursor off-screen on purpose.
- **Control characters in `put`**: each one (C0, DEL, C1, including tabs, `\x1b` and `\r`) is replaced with `U+FFFD`, so text can't inject escape sequences. `\n` is the exception when `wrap=True`.
- **Wide characters** (CJK, emoji): every character counts as one cell for now.
- **`clear(box=None)`**: `None` means the whole window; otherwise clears the given `Box`.
- **`Box(x, y, w, h)`**: a reusable rectangle class for use by other functions too.
- **`wait_event(timeout=None)`**: `None` blocks until an event arrives; a number waits that many seconds and returns `None` on timeout. A non-blocking queue may come later.
- **Events** (tagged union):
  - `Char(ch, ctrl, alt)`: printable characters and Ctrl/Alt combinations,
  - `Key(name, ctrl, alt, shift)`: Up, Down, Left, Right, Home, End, PageUp, PageDown, Insert, Delete, Enter, Tab, Backspace, Escape, F1-F12,
  - `Resize(width, height)`.
  Unparseable input is dropped.
- **Ctrl-C** arrives as a `Char` event; handling it is the program's job (no automatic `KeyboardInterrupt`).

## Terminal APIs

Use exactly the mechanisms below. No curses, no terminfo, no `print` or `sys.stdout` in the library. In code, escape sequences are Python string literals with `\x1b` for ESC, and each gets a comment naming it (CUP, SGR, DECTCEM...).

### OS layer

| Job | API |
| --- | --- |
| File descriptors | Read from fd `0`, write to fd `1`. `screen()` raises `RuntimeError` if `os.isatty(0)` or `os.isatty(1)` is false. |
| Save settings | `saved = termios.tcgetattr(0)`, before changing anything. |
| Enter raw mode | Copy `saved`, change the flags listed below, apply with `termios.tcsetattr(0, termios.TCSAFLUSH, raw)`. Set the flags explicitly instead of calling `tty.setraw`, so the exact mode is visible in the code. |
| Restore settings | `termios.tcsetattr(0, termios.TCSAFLUSH, saved)`. `TCSAFLUSH` also discards unread input, so leftover bytes don't leak into the shell. |
| Terminal size | `os.get_terminal_size(1)`. Cache it: read once on enter and again whenever a `Resize` event is produced, so `width()`/`height()`/`size()` always match the last event the program saw. |
| Resize notification | `signal.signal(signal.SIGWINCH, handler)` with a no-op handler, plus a self-pipe: `r, w = os.pipe()`, both made non-blocking with `os.set_blocking(fd, False)`, and `signal.set_wakeup_fd(w)`. Every `wait_event` call first drains `r` without blocking; if it held a SIGWINCH and the size differs from the cached one, update the cache and return a `Resize` ahead of any queued key events. The size check matters: `uv run` forwards SIGWINCH to the child, which the kernel also signals, so one resize can arrive twice. On exit restore the previous handler and the previous wakeup fd (the return value of `set_wakeup_fd`), and close the pipe. |
| Waiting | `selectors.DefaultSelector()` with fd `0` and `r` registered; `select(timeout)`. |
| Reading | `os.read(0, 4096)`, decoded with `codecs.getincrementaldecoder("utf-8")(errors="replace")`, so a multi-byte character split across two reads is reassembled. |
| Writing | `os.write(1, data)` in a loop until every byte is written; it may write fewer bytes than given. |

Raw mode flags, starting from the saved settings (indexes into the list from `tcgetattr`):

| Field | Change | Why |
| --- | --- | --- |
| `lflag` | clear `ECHO`, `ICANON`, `ISIG`, `IEXTEN` | No echo, no line buffering, Ctrl-C/Z/\ arrive as bytes, no Ctrl-V literal-next |
| `iflag` | clear `BRKINT`, `ICRNL`, `INPCK`, `ISTRIP`, `IXON` | Enter arrives as `\r`, no Ctrl-S/Q flow control, no 8th-bit stripping |
| `oflag` | clear `OPOST` | No `\n` → `\r\n` translation; the library positions everything itself |
| `cflag` | set `CS8` | 8-bit characters |
| `cc` | `VMIN = 1`, `VTIME = 0` | `read()` returns as soon as one byte is available |

### Enter and exit

On enter, after raw mode, write these immediately with `os.write` (not through the user's buffer):

1. `\x1b[?1049h`: alternate screen on.
2. `\x1b[?7l`: auto-wrap off (DECAWM). The library crops and wraps text itself, and with auto-wrap on, writing the bottom-right cell can scroll the screen.

On exit, in this order, again written immediately: `\x1b[0m` (reset style), `\x1b[?25h` (show cursor), `\x1b[?7h` (auto-wrap on), `\x1b[?1049l` (alternate screen off). Then restore the termios settings. Anything still in the user's buffer is discarded, not flushed.

### Output: method to sequence

| Method | Emits | Notes |
| --- | --- | --- |
| `cursor_move(x, y)` | CUP `\x1b[{y+1};{x+1}H` | Updates the tracked cursor position. Positions outside the window are allowed; drawing there is cropped. |
| `cursor_visibility(v)` | DECTCEM `\x1b[?25h` / `\x1b[?25l` | |
| `style(...)`, `reset_style()` | nothing | Only update the current `Style`. SGR is emitted lazily (see Style to SGR). |
| `put(text)` | pending SGR, then for each visible line: CUP + the cropped text | Always emit CUP before each line from the tracked position; never rely on the terminal advancing the cursor across lines. Update the tracked position after writing. |
| `clear()` | pending SGR, then ED `\x1b[2J` | Erases the whole window with the current background color. Cursor unchanged. |
| `clear(box)` | pending SGR, then for each row of the box clipped to the window: CUP + `" " * clipped_width` | Then CUP back to the tracked cursor position. |
| `flush()` | the buffer wrapped in `\x1b[?2026h` ... `\x1b[?2026l` | Synchronized output: the terminal paints the batch at once; terminals without support ignore it. One `os.write` loop, then empty the buffer. |

### Style to SGR

- Track two styles: the **current** one (what the user set) and the **emitted** one (what the terminal has). Before writing text or clearing, if they differ, append one SGR sequence and set emitted = current. Emitted starts as `None` so the first draw always emits.
- Every SGR is a full one that starts with a reset: `\x1b[0;{params}m`. Example, bold red text on the default background: `\x1b[0;1;38;2;255;0;0m`. Don't emit incremental changes: bold and dim share the same "off" code (22), so diffs are error-prone.
- Attribute params: bold `1`, dim `2`, italic `3`, underline `4`, reverse `7`, strikethrough `9`.
- Color params (`"default"` needs no param, since `0` already resets colors):

| Color | Foreground | Background |
| --- | --- | --- |
| `Ansi(n)`, n 0-7 | `30+n` | `40+n` |
| `Ansi(n)`, n 8-15 | `90+(n-8)` | `100+(n-8)` |
| `Indexed(n)` | `38;5;n` | `48;5;n` |
| `Rgb(r, g, b)` | `38;2;r;g;b` | `48;2;r;g;b` |

- CSS strings are parsed when `style()` is called, so `Style` only ever holds parsed colors. Case-insensitive, surrounding whitespace ignored. Accepted forms: `#rgb` (each digit doubled), `#rrggbb`, `rgb(r, g, b)` with integers 0-255, and the 148 named colors of CSS Color Level 4 (including `rebeccapurple` and both `gray`/`grey` spellings). Anything else (`transparent`, alpha channels, `hsl()`, percentages) raises `ValueError`.

### Input: bytes to events

The parser is pure: decoded text in, events out, unit-tested without a terminal. One read can contain several events, so `wait_event` keeps an internal queue and returns a queued event without blocking when there is one.

| Input | Event |
| --- | --- |
| Printable character | `Char(ch)` |
| `\r` (0x0D) | `Key(ENTER)` |
| `\t` (0x09) | `Key(TAB)` |
| 0x7F | `Key(BACKSPACE)` |
| Other 0x01-0x1A | `Char(chr(0x60 + byte), ctrl=True)`, e.g. 0x03 → `Char("c", ctrl=True)` |
| 0x00 | `Char(" ", ctrl=True)` |
| ESC alone | `Key(ESCAPE)` |
| ESC + any other single character | that character's event with `alt=True` |
| `ESC [` ... | CSI, table below |
| `ESC O` + one character | SS3, table below |

| Sequence | Key |
| --- | --- |
| CSI or SS3 `A` / `B` / `C` / `D` | Up / Down / Right / Left |
| CSI or SS3 `H`, CSI `1~`, CSI `7~` | Home |
| CSI or SS3 `F`, CSI `4~`, CSI `8~` | End |
| CSI `2~` / `3~` | Insert / Delete |
| CSI `5~` / `6~` | PageUp / PageDown |
| SS3 `P` `Q` `R` `S`, CSI `11~`-`14~` | F1-F4 |
| CSI `15~` `17~` `18~` `19~` `20~` `21~` `23~` `24~` | F5-F12 |
| CSI `Z` | Tab with `shift=True` |

- **Modifiers**: `CSI 1;{m}{letter}` and `CSI {n};{m}~` carry a modifier parameter `m`; `m - 1` is a bitmask: 1 = shift, 2 = alt, 4 = ctrl. Example: `\x1b[1;5A` is Ctrl+Up.
- **Unknown sequences**: a CSI sequence is `ESC [`, then parameter bytes 0x30-0x3F, intermediate bytes 0x20-0x2F, and one final byte 0x40-0x7E. Consume through the final byte and drop it. An unknown SS3 is `ESC O` plus one character, dropped.
- **Lone ESC**: if the input ends with ESC or an incomplete CSI, wait up to 30 ms (selector timeout) for more bytes before deciding. Nothing arrives: a lone ESC becomes `Key(ESCAPE)`, an incomplete sequence is dropped.

### Not in v0

Don't enable mouse reporting, bracketed paste, focus events, the kitty keyboard protocol or application cursor keys (`?1`). SS3 arrows are still parsed, since some terminals send them anyway.

## Open questions (not yet confirmed by the user)

1. Is the reading of `default_style` above right, and are the six attributes the right set?
2. `clear` colors: proposed to fill with spaces in the current background color and leave the cursor where it was.
3. Python version: proposed 3.11+.