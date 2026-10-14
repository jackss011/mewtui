import pytest

from mewtui import Box


def test_clear_box_fills_rows_and_returns_the_cursor(ctx):
    ctx.cursor_set(1, 1)
    ctx._buffer.clear()
    ctx._emitted_style = ctx._style
    ctx.clear(Box(2, 3, 3, 2))
    assert "".join(ctx._buffer) == "\x1b[4;3H   \x1b[5;3H   \x1b[2;2H"


def test_clear_box_is_clipped_to_the_window(ctx):
    ctx._emitted_style = ctx._style
    ctx.clear(Box(-2, 4, 5, 3))
    assert ctx._buffer[:2] == ["\x1b[5;1H", "   "]
    assert len(ctx._buffer) == 3


def test_clear_box_outside_the_window_does_nothing(ctx):
    ctx.clear(Box(10, 0, 3, 3))
    ctx.clear(Box(0, 0, 0, 3))
    assert ctx._buffer == []


def test_clear_whole_window(ctx):
    ctx._emitted_style = ctx._style
    ctx.clear()
    assert ctx._buffer == ["\x1b[2J"]


def test_negative_box_size_raises():
    with pytest.raises(ValueError):
        Box(0, 0, -1, 2)
