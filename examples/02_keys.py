"""Show each key event as it arrives. Quit with Ctrl-C."""

import mewtui
from mewtui import Char, Key


def describe(event: mewtui.Event) -> str:
    match event:
        case Char(ch, ctrl=ctrl, alt=alt):
            return modifiers(ctrl, alt, False) + repr(ch)
        case Key(name, ctrl=ctrl, alt=alt, shift=shift):
            return modifiers(ctrl, alt, shift) + name.value


def modifiers(ctrl: bool, alt: bool, shift: bool) -> str:
    names = [
        name for name, held in [("Ctrl", ctrl), ("Alt", alt), ("Shift", shift)] if held
    ]
    return "".join(name + "+" for name in names)


with mewtui.screen() as ctx:
    width, height = ctx.size()
    ctx.cursor_move(0, 0)
    ctx.put("Press keys to see their events. Ctrl-C quits.")
    ctx.flush()

    lines: list[str] = []
    while True:
        event = ctx.wait_event()
        if event == Char("c", ctrl=True):
            break
        # Keep the newest events that fit below the header, newest last.
        lines = (lines + [f"{describe(event):<20} {event}"])[-(height - 2) :]
        for row, line in enumerate(lines):
            ctx.cursor_move(0, row + 2)
            ctx.put(line.ljust(width))  # pad with spaces to overwrite the old line
        ctx.flush()
