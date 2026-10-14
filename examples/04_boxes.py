"""Boxes with borders, wrapped text and clipping. Quit with q or Ctrl-C."""

import mewtui
from mewtui import Box, Char, Resize

PARAGRAPH = (
    "This paragraph is one put(text, wrap=True) call. It breaks at the right "
    "edge of the window and every line starts again at the column where the "
    "put began. Resize the window to watch it re-wrap."
)
INSIDE = "Lines split on \\n\nstart at the same\ncolumn.\n\nclear(box) fills it."


def border(ctx: mewtui.Context, box: Box) -> None:
    """Draw a line around the inside edge of box, one cell at a time."""
    right, bottom = box.x + box.w - 1, box.y + box.h - 1
    for x in range(box.x + 1, right):
        ctx.set("─", x, box.y)
        ctx.set("─", x, bottom)
    for y in range(box.y + 1, bottom):
        ctx.set("│", box.x, y)
        ctx.set("│", right, y)
    ctx.set("┌", box.x, box.y)
    ctx.set("┐", right, box.y)
    ctx.set("└", box.x, bottom)
    ctx.set("┘", right, bottom)


def panel(ctx: mewtui.Context, box: Box, color: str, text: str) -> None:
    """A filled, bordered box with text inside it."""
    ctx.style(bg=color)
    ctx.clear(box)
    border(ctx, box)
    ctx.cursor_set(box.x + 2, box.y + 1)
    ctx.put(text, wrap=True)
    ctx.reset_style()


def draw(ctx: mewtui.Context) -> None:
    width, height = ctx.size()
    ctx.reset_style()
    ctx.clear()

    ctx.cursor_set(2, 0)
    ctx.put("q or Ctrl-C quits")

    panel(ctx, Box(2, 2, 26, 7), "#1d3557", INSIDE)

    ctx.cursor_set(32, 2)
    ctx.put(PARAGRAPH, wrap=True)

    # Half of this one hangs off the bottom-right corner and is clipped.
    panel(ctx, Box(width - 14, height - 4, 28, 8), "#6a040f", "Clipped at\nthe edges.")


with mewtui.screen() as ctx:
    ctx.cursor_visibility(False)
    draw(ctx)
    ctx.flush()
    while True:
        match ctx.wait_event():
            case Char("q", ctrl=False) | Char("c", ctrl=True):
                break
            case Resize():
                draw(ctx)
                ctx.flush()
