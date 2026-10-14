import pytest

from mewtui import Rgb


def test_set_draws_and_returns_the_cursor(ctx):
    ctx.cursor_set(1, 1)
    ctx._buffer.clear()
    ctx._emitted_style = ctx._style
    ctx.set("#", 4, 2)
    assert "".join(ctx._buffer) == "\x1b[3;5H#\x1b[2;2H"
    assert (ctx._x, ctx._y) == (1, 1)


def test_set_emits_pending_style(ctx):
    ctx.style(fg=Rgb(255, 0, 0))
    ctx.set("x", 0, 0)
    assert ctx._buffer[0] == "\x1b[0;38;2;255;0;0m"


@pytest.mark.parametrize(("x", "y"), [(-1, 0), (10, 0), (0, -1), (0, 5)])
def test_set_off_screen_is_dropped(ctx, x, y):
    ctx.set("#", x, y)
    assert ctx._buffer == []


def test_set_replaces_control_characters(ctx):
    ctx._emitted_style = ctx._style
    ctx.set("\x1b", 0, 0)
    assert ctx._buffer[1] == "�"


@pytest.mark.parametrize("char", ["", "ab"])
def test_set_needs_one_character(ctx, char):
    with pytest.raises(ValueError):
        ctx.set(char, 0, 0)
