"""Text attributes and every kind of color. Quit with q or Ctrl-C."""

import mewtui
from mewtui import Ansi, Char, Indexed, Resize, Rgb, Style

# Light grey on a dark blue-grey; clear() and reset_style() use these.
mewtui.default_style = Style(fg=Rgb(220, 220, 230), bg=Rgb(30, 30, 46))


def heading(ctx: mewtui.Context, y: int, text: str) -> None:
    ctx.cursor_set(2, y)
    ctx.style(bold=True)
    ctx.put(text)
    ctx.reset_style()


def draw(ctx: mewtui.Context) -> None:
    ctx.reset_style()
    ctx.clear()

    heading(ctx, 1, "Attributes")
    ctx.cursor_set(2, 2)
    for name in ["bold", "dim", "italic", "underline", "reverse", "strikethrough"]:
        ctx.style(
            bold=name == "bold",
            dim=name == "dim",
            italic=name == "italic",
            underline=name == "underline",
            reverse=name == "reverse",
            strikethrough=name == "strikethrough",
        )
        ctx.put(name)
        ctx.cursor_delta(2, 0)
    ctx.reset_style()

    heading(ctx, 4, "Ansi 0-15 (follow the terminal theme)")
    ctx.cursor_set(2, 5)
    for index in range(16):
        ctx.style(bg=Ansi(index))
        ctx.put("   ")
    ctx.reset_style()

    heading(ctx, 7, "Indexed 16-255")
    for row in range(7):
        ctx.cursor_set(2, 8 + row)
        for index in range(16 + 36 * row, min(16 + 36 * (row + 1), 256)):
            ctx.style(bg=Indexed(index))
            ctx.put(" ")
    ctx.reset_style()

    heading(ctx, 16, "Rgb")
    ctx.cursor_set(2, 17)
    steps = 64
    for i in range(steps):
        ctx.style(bg=Rgb(255 * i // (steps - 1), 80, 255 - 255 * i // (steps - 1)))
        ctx.put(" ")
    ctx.reset_style()

    heading(ctx, 19, "CSS strings")
    ctx.cursor_set(2, 20)
    for css in [
        "tomato",
        "gold",
        "#7fffd4",
        "#f8a",
        "rgb(100, 149, 237)",
        "rebeccapurple",
    ]:
        ctx.style(fg=css)
        ctx.put(css)
        ctx.cursor_delta(2, 0)
    ctx.reset_style()

    ctx.cursor_set(2, 22)
    ctx.style(dim=True)
    ctx.put("q or Ctrl-C quits")
    ctx.reset_style()


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
